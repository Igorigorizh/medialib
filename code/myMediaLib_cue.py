# -*- coding: utf-8 -*-
import re
import os
import datetime
import chardet
import logging
import zlib
import operator
import collections

from os import curdir, sep,getcwd
import os.path

from mutagen.apev2 import APEv2, error
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.monkeysaudio import MonkeysAudioInfo

import mutagen

logger = logging.getLogger('controller_logger.cue')

def myMusicStr2TimeDelta(strTime):
	l = [int(a) for a in strTime.split(':')]
	return datetime.timedelta(hours=l[0],minutes=l[1],seconds=l[2],microseconds=l[3])

def sec2hour(sec):
	return '%02i'%(int(sec/3600))+':'+'%02i'%(int(int(sec%3600)/60))+':'+'%02i'%(sec%60)+':00'
	
def parseCue(fName,*args):
	# Два реежима потрэковый и однообраз сильно отличаются по сценариям извлечения данных
	# 1. Время можно вычислить из INDEX разности для Cue - однообраз, для трэкового - из физических файлов
	# индексы в image CUE могут быть с pregap и его надо игнорировать, беря только вторые индексы для вычисления времени	
	# в режиме only_file в single image возвращает количество cue_tracks_number = 0 => чтобы узнать реальное количество трэков
	# надо вызывать без параметров
	try:
		logger.debug('in parseCue - start')
	except:
		print 'No logger attached at local execution'
		pass
	char_codec = line_album_codec = line_file_codec = line_track_codec = line_perform_main_codec = line_perform_track_codec = {}
	cue_crc32 = 0
	if not isinstance(fName, unicode):
		char_codec = chardet.detect(fName)
		try:
			fName = fName.decode(char_codec['encoding'])
			
		except Exception, e:
			logger.critical('Exception at 50 [%s] in parseCue'%(str(e)))	
			return {'Error':e}
		
	try:
		f = open(fName,'r')
	except Exception, e:
		print 'File not found:',fName,char_codec
		logger.critical('Exception at 57[%s] in parseCue'%(str(e)))	
		return {'Error':e}
	
	l = f.readlines()
	f.close()
	track_flag = False
	album = ''
	full_time = ''
	orig_file = ''
	orig_file_path = ''
	orig_file_pathL = []
	perform_main = ''
	track_num = 0
	trackD = {}
	bitrate = 0
	got_file_info = False
	orig_file_path_exist = False
	is_cue_multy_tracks = False
	is_non_compliant_eac_cue = False
	check_fileL = []
	exists_track_stackL = []
	temp_track_stackL  = []
	delta = 0
	bitrateL = []
	
	try:
		cue_crc32 = zlib.crc32(fName.encode('raw_unicode_escape'))
	except Exception, e:
		print 'Error crc32 generate'
		logger.critical('Exception [%s] in parseCue  [cue crc32 generation]'%(str(e)))	
		return {'Error':e}
		
	# define most possible coding schema	
	cue_termsL = ['file ','title ','performer ']
	codec_freqL = []
	tobe_suppressed_codecL = ['MacCyrillic','ascii']
	for a in l:
		for term in cue_termsL:
			if a.lower().strip().find(term) == 0:
				codec_freqL.append(chardet.detect(a)['encoding'])
	counter=collections.Counter(codec_freqL)
	most_codec = str(counter.most_common(1)[0][0])
	
	# belew is heuristik aproach for codec change when 'ascii' is a major but also local specifik is met so ignor ascii! 
	# better aproach 1. Предотвратить появление копии потрэковой альбома если это CUE
	# 2. выбирать кодек файла на втором проходе, если при первомо происходит неправильный выбор кодировки файла CUE
	# 3. надо делать несколько проходный прелоад сценарий
	if len(counter)>1 and most_codec in tobe_suppressed_codecL:
		most_codec = str(counter.most_common(2)[1][0])
		#print 'codec changed:',most_codec,counter.most_common(1)[0][0]
		logger.warning('in parseCue - codec changed from:%s to %s '%(str(counter.most_common(1)[0][0]),str(counter.most_common(2)[1][0])))	
		
	logger.debug('in parseCue - codec statistic:%s'%(str(counter)))
	#most_codec = 'cp1251'
	
	print "----------------^^^^ParseCue-stamp^^^^^^^^^^^^^^^^^^----------"
	print [most_codec],counter.most_common(1)
		
	for a in l:
		
		if a.lower().strip().find('file ') == 0:
			
			#print chardet.detect(a)
			orig_file_path = orig_file = ''
			
			if track_flag:
				track_flag = False
			lst = re.split('([^"]*")(.*)("[^"]*)', a)
			line_file_codec = chardet.detect(lst[2])
			#print line_file_codec
			#print
			
			try:	
				#orig_file = lst[2].decode(line_file_codec['encoding'])
				orig_file = lst[2].decode(most_codec)
				
			except UnicodeDecodeError, e:
				print 'decoding catch at cueParse:',orig_file
				orig_file = lst[2].decode('raw_unicode_escape')
			except Exception, e:	
				orig_file = 'decode_utf8_Error'.decode('utf8')
			
			orig_file_path = fName[:fName.rfind('\\')+1]+orig_file
			fType = orig_file[orig_file.rfind('.')+1:]
			
			orig_file_path_exist = False
			if os.path.exists(orig_file_path):
				orig_file_path_exist = True
				if orig_file_path not in exists_track_stackL:
					exists_track_stackL.append(orig_file_path)
			else:
				print 'Check CUE:',[orig_file_path] 
				logger.warning('in parseCue - incomplient orig file not found  [%s]'%(orig_file_path))	

			
			if len(exists_track_stackL)>1:
				is_cue_multy_tracks = True	
			
			
				
			if orig_file_path_exist and 'with_bitrate' in args:	
				if fType.lower() == 'ape':
					try:
						f = open(orig_file_path,'rb')
					except IOError, e:	
						print e,
						logger.critical('Exception at 131 [%s] in parseCue  [cue crc32 generation]'%(str(e)))	
						return {'Error':e}
						
					#print 'orig_file_path=',orig_file_path
					try:
						m = MonkeysAudioInfo(f)
						f.close()
					except Exception, e:
						print 'probably MonkeysAudioHeaderError_1',orig_file_path
						f.close()
						logger.critical('Exception at 141 [%s] in parseCue  [MonkeysAudioHeaderError_1]'%(str(e)))	
						return {'Error':e}
					
					try:	
						tmp_length = sec2hour(m.length)
						full_time = myMusicStr2TimeDelta(tmp_length)
						bitrate = int(os.path.getsize(orig_file_path)*8/1000/m.length)
					except :
						print 'probably MonkeysAudioHeaderError_2',orig_file_path	
						logger.critical('Exception at 151 [%s] in parseCue  [MonkeysAudioHeaderError_2]'%(str(e)))	
						return {'Error':e}
						#print full_time
					
						
				elif fType.lower() == 'flac':	
					try:
						audio = FLAC(orig_file_path)
					except Exception,e :
						print 'probably FLAC error',orig_file_path
						return {'Error':e,'error path':orig_file_path}
					tmp_length = sec2hour(audio.info.length)
					full_time = myMusicStr2TimeDelta(tmp_length)
					#bitrate = int(os.path.getsize(orig_file_path)*8/1024/audio.info.length)
					bitrate = int(round(float(audio.info.bitrate)/1000))
			
			
			
			if orig_file_path <> '':
				orig_file_path_crc32 = zlib.crc32(orig_file_path.encode('raw_unicode_escape'))
				orig_file_pathL.append({'orig_file_path':orig_file_path,'file_exists':orig_file_path_exist,'BitRate':bitrate,'Time':full_time,'file_crc32':orig_file_path_crc32})	
					
			continue
			
		if 'only_file' in args:
			continue	
	
		if a.lower().strip().find('track ') == 0:
			track_flag=True
			tracL = a.split()
		
		# Находимся в секции TRACK	и получаем новый номер трэка
			if tracL[0].lower() == 'track' and tracL[2].lower() == 'audio':
				track_num = int(tracL[1])
				trackD[track_num]={'Title':'','Album':'','BitRate':0,'OrigFile':'','Time':'00:00','Performer':''}
				
				
				#Делаем проверку для multytrack, что к этому моменту для трэка > 1
				if track_num >1:
					orig_file_path_number = len(orig_file_pathL)
					if orig_file_path_number > 1 and orig_file_path_number == track_num:
						pass
					else:	
						is_non_compliant_eac_cue = True
				continue


		if a.lower().strip().find('title ') == 0 and not track_flag and orig_file_pathL == []:
			lst = re.split('([^"]*")(.*)("[^"]*)', a)
			album = lst[2].strip()
			
			line_album_codec = chardet.detect(lst[2])
			continue
		
		elif a.lower().strip().find('performer ') == 0 and not track_flag:
			lst = re.split('([^"]*")(.*)("[^"]*)', a)
			try:
				line_perform_main_codec = chardet.detect(lst[2])
				#perform_main = lst[2].strip().decode(line_perform_main_codec['encoding'])
				perform_main = lst[2].strip().decode(most_codec)
				
			except UnicodeDecodeError, e:	
				perform_main = lst[2].strip().decode('raw_unicode_escape')
			except Exception, e:
				perform_main="decode_utf8_Error perform_main".decode('utf8')
				print 'error:',lst,l[0],l[1],l[2],l[3],l[4],l[5]
			continue	


		if a.lower().strip().find('title') == 0 and track_flag and track_num > 0:
#			print 'title here!!!',track_num
			lst = re.split('([^"]*")(.*)("[^"]*)', a)
			try:
				line_track_codec = chardet.detect(lst[2])
			except Exception, e:
				logger.critical('Exception [%s] in parseCue  [at title chardet]'%(str(e)))	
				logger.critical('Exception [%s] in parseCue  [at title chardet-2]'%(str([a,track_num])))	
				print 'parseCue Error: line',track_num
				return {'Error':str(e),'ErrorData':[lst,a,track_num]}
#			raw_input(a)
			try:
				#trackD[track_num]['Title']=lst[2].strip().decode(line_track_codec['encoding'])
				trackD[track_num]['Title']=lst[2].strip().decode(most_codec)
			except UnicodeDecodeError, e:
				trackD[track_num]['Title']=lst[2].strip().decode('raw_unicode_escape')
			except Exception, e:
				trackD[track_num]['Title']='decode_utf8_Error'.decode('utf8')
				trackD[track_num]['TitleUndecode']=lst[2]
				
			try:		
				trackD[track_num]['Album']=album.decode(line_album_codec['encoding'])
			except UnicodeDecodeError, e:
				trackD[track_num]['Album']=album.decode('raw_unicode_escape')
			except Exception, e:
				trackD[track_num]['Album']='decode_utf8_Error'.decode('utf8')
				
			
#			
		elif a.lower().strip().find('performer ') == 0 and track_flag and track_num > 0:
#			print 'rerformer here!!!',track_num
			lst = re.split('([^"]*")(.*)("[^"]*)', a)
			line_perform_track_codec = chardet.detect(lst[2])
			try:
				#trackD[track_num]['Performer']=lst[2].strip().decode(line_perform_track_codec['encoding'])
				trackD[track_num]['Performer']=lst[2].strip().decode(most_codec)
#				print lst
			except Exception, e:
				logger.critical('Exception [%s] in parseCue  [at performer]'%(str(e)))	
				pass
			try:	
				trackD[track_num]['Performer_CRC32'] = zlib.crc32(trackD[track_num]['Performer'].lower().encode('raw_unicode_escape'))	
			except Exception, e:
				logger.critical('Exception [%s] in parseCue  [at performer crc32]'%(str(e)))	
				pass	
				
		elif a.lower().strip().find('index ') == 0 and track_flag and track_num > 0:
#			print 'indx here!!!',track_num
			lst = a.split()
			index = lst[1]
			
			index_time = '00:'+lst[2]
			
			if int(index) == 0:
				trackD[track_num]['index']=[index_time,0]
			elif int(index) == 1:		
				# Поддержка нескольких индексов INDEX 1 и INDEX 0
				if 'index' in trackD[track_num]:
					# один INDEX уже есть, заводим второй индекс
					trackD[track_num]['index']=[trackD[track_num]['index'][0],index_time]
				else:
					# регистрирует первый индекс
					trackD[track_num]['index']=[index_time,index_time]
				
			
				cur_delta = myMusicStr2TimeDelta(trackD[track_num]['index'][1])-myMusicStr2TimeDelta(trackD[track_num]['index'][0])
				
				# Только для single IMAGE вычисляем длину трэка в секундах как разница между соседнмини трэками, только однофайлового CUE	
				if track_num > 1 and not is_cue_multy_tracks:
					try:
						delta = myMusicStr2TimeDelta(trackD[track_num]['index'][1])-myMusicStr2TimeDelta(trackD[track_num-1]['index'][1])-cur_delta
					except Exception,e:	
						print 'Exception [%s] in parseCue  [at myMusicStr2TimeDelta], check time',e
						logger.critical('Exception [%s] in parseCue  [at myMusicStr2TimeDelta]'%(str(e)))	
						delta = datetime.timedelta(0)
						
					trackD[track_num-1]['Time'] = str(delta)[2:7]
	
	
	if is_cue_multy_tracks:
		if len(exists_track_stackL) <> len(orig_file_pathL):
			is_non_compliant_eac_cue = True
	
	
	
	if 'only_file' in args:
		pass
		if track_num == 0 and len(orig_file_pathL)>1:
			track_num = len(orig_file_pathL)
	else:
		
		for a in trackD:
			if trackD[a]['Performer'] =='':
				trackD[a]['Performer'] = perform_main 
				try:
					trackD[a]['Performer_CRC32'] = zlib.crc32(perform_main.encode('raw_unicode_escape'))
				except Exception, e:
					logger.critical('Exception [%s] in parseCue  [at performer main crc32]'%(str(e)))	
					pass		
			if trackD[a]['Album'] =='':
				trackD[a]['Album'] = album 	
				
			# For image cue restore OrigFile from 1st track	
			if not is_cue_multy_tracks:
				trackD[a]['OrigFile'] = orig_file_pathL[0]['orig_file_path']
				if 'with_bitrate' in args:	
					trackD[a]['BitRate']=orig_file_pathL[0]['BitRate']
			# for Multy track replicate from orig_file_pathL	
			elif is_cue_multy_tracks:	
				orig_file = orig_file_pathL[a-1]['orig_file_path']
				try:	
					trackD[a]['OrigFile']=orig_file
				except UnicodeDecodeError, e:
					trackD[a]['OrigFile']=orig_file.decode('raw_unicode_escape')
				except Exception, e:	
					trackD[a]['OrigFile']='decode_utf8_Error'.decode('utf8')
				
				if 'with_bitrate' in args:	
					trackD[a]['BitRate']=orig_file_pathL[a-1]['BitRate']	
					time = str(orig_file_pathL[a-1]['Time'])
					if time[:2]	== '0:':
						time=time[2:7]
					trackD[a]['Time'] = time
					
					
		if 'with_bitrate' in args and not is_cue_multy_tracks:
		# для вычисления времени последнего трэка нужна длина всего файла, это только с with_bitrate
			try:
				delta = str(full_time - myMusicStr2TimeDelta(trackD[track_num]['index'][1]))
			except Exception, e:
				print e
				print 'Error in parseCue-> myMusicStr2TimeDelta', trackD[track_num],track_num
				logger.critical('Exception at 331 [%s] in parseCue  [myMusicStr2TimeDelta]'%(str(e)))	
				logger.critical('Exception at 331 [%s] in parseCue  [myMusicStr2TimeDelta]-2'%(fName))	
				
			
			if delta[:2] == '0:':
				delta=delta[2:7]
			trackD[track_num]['Time'] = delta
		elif 'with_bitrate' not in args and not is_cue_multy_tracks:
			# без длины всего образа нельзя вычислить последний трэк
			trackD[track_num]['Time'] = '00:00'
	

#	print 'in parseCue - finished with [%s %s]'%(str(len(exists_track_stackL)),str(len(orig_file_pathL)))
	
#	for a in exists_track_stackL:
#		print a
	logger.debug('in parseCue - finished with [%s %s]'%(str(len(exists_track_stackL)),str(len(orig_file_pathL))))	
	return {'trackD':trackD,'is_non_compliant_eac_cue':is_non_compliant_eac_cue,'is_cue_multy_tracks':is_cue_multy_tracks,'orig_file_pathL':orig_file_pathL,'fType':fType,'cue_tracks_number':track_num,'cue_crc32':cue_crc32,'cue_f_name':fName}
	
def simple_parseCue(fName,*args):
	fType = ''
	try:
		f = open(fName,'r')
	except:
		print 'File not found:',fName
		return None
	l = f.readlines()
	f.close()
	track_flag = False
	album = ''
	full_time = ''
	orig_file = ''
	orig_file_path = ''
	perform_main = ''
	track_num = 0
	trackD = {}
	got_file_info = False
	for a in l:

		if a.lower().strip().find('track ') == 0:
			track_flag=True
			tracL = a.split()
			
			if tracL[0].lower() == 'track' and tracL[2].lower() == 'audio':
				track_num = int(tracL[1])
		#		trackD[track_num]={'Title':''}
				continue


		if a.lower().strip().find('file ') == 0 and not track_flag:
			
			
			lst = re.split('([^"]*")(.*)("[^"]*)', a)
			orig_file = lst[2]
			orig_file_path = fName[:fName.rfind('\\')+1]+orig_file
			fType = orig_file[orig_file.rfind('.')+1:]
			#print 'orig_file_path',orig_file_path,fType
			if fType == '':
				print 'Error in fType:',a
			continue
	
	songL = []	
	for i in range(1,track_num+1):
		songL.append(fName+','+str(i))
	if fType == '':
		print 'Error in fType:',orig_file_path
	return {'orig_file':orig_file,'orig_file_path':orig_file_path,'fType':fType,'songL':songL,'cue_tracks_number':track_num} 
	
def checkCue_inLibConsistenc_folder(init_dirL,*args):
# ???? ????????? ??????????? ?? ?????? ???? ? CRC32 c ?????? CUE
#r = myMediaLib.collectMyMediaLib_folder(['G:\\MUSIC\\ORIGINAL_MUSIC'])
	cnt = 0
	allmFD = {}
	cueD = {}
	cueDupl = {}
	notRelevCue = {}
	cueDupResD = {}
	flac_no_cueL = []
	ape_num = flac_num = all_alb_cnt = flac_no_cue_num = 0
	for init_dir in init_dirL:
		for root, dirs, files in os.walk(init_dir):
			cue_flag = False
			origf = ''
			ftype = ''

			for a in files:
			       #if a.find('.ape') > 0 or a.find('.flac')
				#if "image" in a:
				#	print a  
				#if "ergole" in a:
				#	print a   
				cue_flag = False
				#if a[a.rfind('.'):].lower().find('.cue') >= 0:
				if '.cue' in a:
					origf = ''
					ftype = ''
					
					try:
						cue_name = (root+'\\'+a).decode('utf-8').encode('cp1251')
				
					except:
						cue_name = (root+'\\'+a)

					try:	
						origfD = simple_parseCue(cue_name)	
					except NameError:
						import myMediaLib
						origfD = myMediaLib.simple_parseCue(cue_name)	
	#return {'orig_file':orig_file,'orig_file_path':orig_file_path,'fType':fType,'songL':songL} 
	
					try:
						if os.path.exists(origfD['orig_file_path']):
							cue_dirname = os.path.dirname(origfD['orig_file_path'])
							check_dircrc32 =  zlib.crc32(cue_dirname.decode('cp1251').encode('utf-8').lower())
							if check_dircrc32 in cueDupl :
								cueDupl[check_dircrc32]['dupL'].append((origfD['orig_file_path'],a)) 
							else:
								cueDupl[check_dircrc32] = {'dupL':[(origfD['orig_file_path'],a),],'dirName':cue_dirname,'cueFile':a}
								
							cue_flag = True
							if origfD['fType'].lower() == 'flac':
								flac_num+=1
							elif origfD['fType'].lower() == 'ape':
								ape_num+=1
							else:
								print origfD['fType']
							origf = origfD['orig_file_path']
							ftype = origfD['fType']
							crc32 = zlib.crc32(origf.decode('cp1251').encode('utf-8').lower())
							last_modify_date = 0
							try:
								last_modify_date = os.stat(cue_name).st_mtime
							except:
								print 'eroror cue time',origfD['orig_file_path']
								pass
							cueD[crc32]={'dir':root,'filename':a,'file':origf,'ftype':ftype,'songL':origfD['songL'],'last_modify_date':last_modify_date,'cueFName':cue_name}
						else:
							if  zlib.crc32(cue_name) in  notRelevCue:
								notRelevCue[zlib.crc32(cue_name)]['fL'].append(origfD['orig_file_path']) 
							else:
								notRelevCue[zlib.crc32(cue_name)] = {'fL':[origfD['orig_file_path'],],'cueFile':a}
							#print 'Cue not relevant:',origfD['orig_file_path']
							continue
					except:
						print 'error:',origfD
					#break
			
			continue
			
			for a in files:
				
				ftype = None
				if a[a.rfind('.'):].lower().find('.ape') >= 0:
					ftype = 'ape'
					
				elif a[a.rfind('.'):].lower().find('.flac') >= 0:
					ftype = 'flac'
				elif a[a.rfind('.'):].lower().find('.mp3') >= 0:
					ftype = 'mp3'
				
				if	ftype <> None:
					fname = (root.decode('cp1251').encode('utf-8')+'\\'+a.decode('cp1251').encode('utf-8')).lower() 
					orig_fname = root+'\\'+a 
					
					crc32 = zlib.crc32(fname)
					#if crc32 == 1133272172:
					#	return fname
					last_modify_date = 0
					try:
						last_modify_date = os.stat(orig_fname).st_mtime
					except:
						pass
					
					
					pos = root.rfind('\\')
					#pos_1 = a[:pos_2-2].rfind('\\')+1
					album = root[pos+1:]
					#print root
					if crc32 in cueD:
						for b in cueD[crc32]['songL']:
							crc32_i = zlib.crc32((b.decode('cp1251').encode('utf-8')).lower())
							pos = b.rfind(',')
							allmFD[crc32_i] = {'orig_fname':cueD[crc32]['file'],'last_modify_date':cueD[crc32]['last_modify_date'],'album':album,'album_crc32':zlib.crc32((root.decode('cp1251').encode('utf-8')).lower()),'file':b.lower(),'cueNameIndx':b[:pos],'ftype':ftype,'cue':'X'}
					else:
						allmFD[crc32] = {'orig_fname':orig_fname,'last_modify_date':last_modify_date,'album':album,'album_crc32':zlib.crc32((root.decode('cp1251').encode('utf-8')).lower()),'file':fname,'ftype':ftype,'cueNameIndx':None}
			
			if 'stat' not in args:
				continue
				
			for a in files:
				#crc32 = zlib.crc32(str(root).lower()+'\\'+a.lower())
				#allmFL[crc32] = str(root).lower()+'\\'+a.lower() 
				if a[a.rfind('.'):].find('.mp3') >= 0:
					all_alb_cnt += 1
					break
				elif a[a.rfind('.'):].find('.ape') >= 0:
					all_alb_cnt += 1
					break
				elif a[a.rfind('.'):].find('.flac') >= 0:
					if not cue_flag:
						flac_no_cue_num +=1
						flac_no_cueL.append(root)
					else:
						#print 'cue',
						pass
					all_alb_cnt += 1
					break
			cnt+=1
			if cnt%100 == 0:
				print '.',len(allmFD),
				
	for a in cueDupl:
		if len(cueDupl[a]['dupL'])>1:
			cueDupResD[a] = cueDupl[a]
	return 	{'cueDupl':cueDupResD,'notRelevCue':notRelevCue}	
	
	if 'stat' in args:
		print
		print 'cueL:',len(cueD),'ape_num:',ape_num,'flac_num:',flac_num,'flac_no_cue_num:',flac_no_cue_num,'all_alb_cnt:',all_alb_cnt
		return {'allmFD':allmFD,'cueL':cueD,'flac_no_cueL':flac_no_cueL,'ape_num':ape_num,'flac_num':flac_num,'all_alb_cnt':all_alb_cnt,'flac_no_cue_num':flac_no_cue_num}
	else:
		return {'allmFD':allmFD,'cueL':cueD}		
def cue_check_and_error_correct(fName,separator,seqL,*args):
	fType = ''
	try:
		f = open(fName,'r')
	except:
		print 'File not found:',fName
		return None
	l = f.readlines()
	f.close()
	track_flag = False
	album = ''
	full_time = ''
	orig_file = ''
	orig_file_path = ''
	perform_main = ''
	track_num = 0
	trackD = {}
	resL = []
	got_file_info = False
	do_job = False
	for a in l:
		if 'TRACK 01 AUDIO' in a:
			do_job = True
			
		if not do_job:
			resL.append(a)
			continue
			
		pos = a.find('"')+1
		if 'separate' in args:

			if a.lower().strip().find('performer') == 0:
				index = None
				if seqL[0].lower() == 'artist':
					index = 0
				else:
					index = 1

				if index == None:
					print 'Error'
					return 0


				
				partsL = a[pos:-2].split(separator)
				print partsL
				try:
					line = '\t'+'PERFORMER "'+partsL[index].strip()+'"'+'\n'
				except:
					resL.append(a)
					print 'Eroror',a
					continue		
			elif a.lower().strip().find('title') == 0:
				index = None
				if seqL[0].lower() == 'artist':
					index = 1
				else:
					index = 0

				if index == None:
					print 'Error'
					return 0
					
					
				
				partsL = a[pos:-2].split(separator)
				print partsL
				try:
					line = '\t'+'TITLE "'+partsL[index].strip()+'"'+'\n'
				except:
					resL.append(a)
					print 'Eroror',a
					continue	
			else:
				line = a
			resL.append(line)
	file_name_new =	'corrected_'+fName
	f = open(file_name_new,'w')
	l = f.writelines(resL)
	f.close()		
	
def GetTrackInfoVia_ext(filename,ftype):
	logger.debug('in GetTrackInfoVia_ext - start')
	#'pL_info':pL_info
	audio = None
	bitrate = 0
	time_sec = 0
	if ftype.lower() == 'flac':
		try:
			
			audio = FLAC(filename)
			
			if audio.info.length <> 0:
			
				bitrate = int(round(float(audio.info.bitrate)/1000))
				tmp_length = sec2hour(audio.info.length)
				full_time = myMusicStr2TimeDelta(tmp_length)
				time_sec = int(audio.info.length)
				time = full_time
			
		except Exception, e:	
			logger.critical('Exception in GetTrackInfoVia_ext: %s'%(str(e)))	
		except IOError, e:
			logger.critical('Exception in GetTrackInfoVia_ext: %s'%(str(e)))	
			return {"title":filename[filename.rfind('\\')+1:-(len(ftype)+1)],"artist":'No Artist',"album":'No Album',"bitrate":0,'time':'00:00','ftype':ftype}
		except :	
			logger.critical('Exception in GetTrackInfoVia_ext: %s'%(str('unknown mutagen error')))	
			
		
		
			
			
	elif ftype.lower() == 'mp3':		
		try:
			audio = MP3(filename, ID3=EasyID3)
		except IOError, e:
			logger.critical('Exception in GetTrackInfoVia_ext: %s'%(str(e)))	
			return {"title":filename[filename.rfind('\\')+1:-(len(ftype)+1)],"artist":'No Artist',"album":'No Album',"bitrate":0,'time':'00:00','ftype':ftype}
		except:
			logger.critical('Strange mp3 error at 639 myMediaLib_cue:')	
			print 'Strange mp3 error at 1524 myMediaLib:',filename
			return {"title":filename[filename.rfind('\\')+1:-(len(ftype)+1)],"artist":'No Artist',"album":'No Album',"bitrate":0,'time':'00:00','ftype':ftype}	
			

		
		try:
			bitrate = audio.info.bitrate/1000	
		except:
			print 'audio=:',audio		
		
			
	elif ftype == 'ape' or ftype == 'apl':                          
		m_audio = None
		try:	
			f = open(filename,'rb')
			m_audio = MonkeysAudioInfo(f)
			f.close()
			if m_audio.length <> 0:
				bitrate = int(os.path.getsize(filename)*8/1000/m_audio.length)
			
		except IOError:
			print 'm_audio.error',filename, ' ---> time and avrg bitrate will not be availble'
			pass
			
			
		try:
			audio=APEv2(filename)
			
			
			
		except IOError:
			return {"title":filename[filename.rfind('\\')+1:-(len(ftype)+1)],"artist":'No Artist',"album":'No Album',"bitrate":bitrate,'time':'00:00','time_sec':0,'ftype':ftype}	
		
	if audio == None:
		return {"title":filename[filename.rfind('\\')+1:-(len(ftype)+1)],"artist":'No Artist',"album":'No Album',"bitrate":bitrate,'time':'00:00','time_sec':0,'ftype':ftype}	
		
		#if a == 0:
		#	time = cur_time
		#else:
		#	time = '00:00'
				
	infoD = {}
	if ftype == 'ape' or ftype == 'apl':
		try:
			time =  '%6s'%sec2min(int(m_audio.length))
			time_sec = int(m_audio.length)
			#print 'timeOk!   ',time
		except:
			time = '00:00'
	elif ftype == 'mp3':
		try:
			time =  '%6s'%sec2min(int(audio.info.length))
			time_sec = int(audio.info.length)
			#print 'timeOk!   ',time
		except:
			time = '00:00'
			time_sec = 0
	#return audio	
	for c in ['title','artist','album','tracknumber','date','genre']:
		try:
			c in audio
		except:
			print audio
			continue
		if c in audio:
			#print audio[c]
			try:
				if ftype == 'mp3':
					item = audio[c].value.strip().decode('cp1251').encode('utf8')
				else:
					item = audio[c].value.strip()
			except AttributeError:
				try:
					item = audio[c][0]
				except:
					print audio[c],c
					
				#if ftype == 'mp3':
					#item = ''.join([chr(ord(b)) for b in item]).decode('cp1251').encode('utf8')	
				infoD[c] = item
					
				continue
			except ValueError:
				pass
			
			try:
				audio[c].__unicode__()
			except:
				item = audio[c].value.strip().decode('cp1251').encode('utf8')
			infoD[c] = item	
		else:
			if c == 'title':
				infoD[c] = filename[filename.rfind('\\')+1:-(len(ftype)+1)]
			elif c == 'tracknumber':			
				infoD[c] = 0
			else:
				infoD[c] = 'NA '+c		
				
				
	infoD['bitrate'] = bitrate
	
	time = str(time)
	if time[:2]	== '0:':
		time=time[2:7]
		
	infoD['time'] = time
	infoD['time_sec'] = time_sec
	infoD['ftype'] = ftype
	logger.debug('in GetTrackInfoVia_ext - finished')
	
	return 	infoD				
	
def generate_play_list_from_fileData(trackLD,album_crc32):
	logger.debug('in generate_play_list_from_fileData - start')
	is_cue = False
	is_image = False
	trackL = []
	temp_trackL = []
	for a in trackLD:
		if trackLD[a]['album_crc32'] == album_crc32:
			if 'cue' in trackLD[a]:
				is_cue = True
				#print "CUE",
			if trackLD[a]['file'] not in trackL:
				trackL.append(trackLD[a]['file'])
				if is_cue:
					try:
						temp_trackL.append((trackLD[a]['file'],int(trackLD[a]['cueNameIndx'])))
					except Exception, e:
						logger.critical('Error: in generate_play_list_from_fileData [%s]'%str(e))
						logger.critical('Error: in generate_play_list_from_fileData skipped [%s]'%str(a))
						logger.critical('Error: in generate_play_list_from_fileData skipped [%s]'%(trackLD[a]['file']))
						continue
				#print trackLD[a]['file']
	print len(trackL),'isCue',is_cue
	# if CUE then simple run cue with winamp
	if is_cue and len(trackL) > 0:
		#pos = trackL[0].rfind(',')
		#cue_file = trackL[0][:pos]
		#print cue_file
		temp_trackL.sort(key=operator.itemgetter(1))
		logger.debug('in generate_play_list_from_fileData - cue Finished')
		return [item[0] for item in temp_trackL]
			
		 
		
	if not is_cue and  len(trackL) > 0:
		trackL.sort()
		logger.debug('in generate_play_list_from_fileData - not cue Finished')
		return trackL
		
	logger.critical('in generate_play_list_from_fileData - Error Finished')	
	return	