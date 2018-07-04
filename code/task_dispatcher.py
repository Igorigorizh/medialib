# -*- coding: utf-8 -*-
import sched, time
import threading
import time
import myMediaLib_adm
import myMediaLib_tools
import logging

mymedialib_cfg = 'C:\\My_projects\\MyMediaLib\\mymedialib.cfg'
s=sched.scheduler(time.time, time.sleep)
s2=sched.scheduler(time.time, time.sleep)

global start_time
start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

"""
#************************* Управление событиями **************
0. To-Do dev.task: сейчас список hardcoded, сделать его параметризированным из DB
1.события: update_lib,update_lib_cur_dir,del_missing_lib, add_new_album, статсусы: 0-new ,1 - running, 2 - finished
2.функции:  
	myMediaLib_adm.triggerBatchJob_via_event -> инициация задания из myMediaLib_controller.do_admin по трем событиям из п.1
	myMediaLib_adm.get_Tasks_in_queue -> получение очереди актуальных заданий для выполнения
	myMediaLib_adm.maintain_Task_for_event - выставить текущий life-status задания 
3. Сценарий. а. получение из UI задания в контроллере метод: do_admin и его регестрация в БД func: triggerBatchJob_via_event, б. в диспетчере задач (эта программа) постоянное сканирование событий по новым заданиям - и запуск соответсвующего сценария. проставление статуса окончания.


"""

def do_daemon_control(aCor,corpusControlList,loginD):

	while 1:
		time.sleep(1)

		if len(aCor) == 0:
			break
	  	s2.enter(1, 5, rss_Monitor_GUI,(aCor,corpusControlList,loginD))
		s2.run()
		
				
	print '\n', 'rss Monitor Stopped'
	raw_input('press any key ...')
	
def run_forever():
	dirAllL = ['G:\\MUSIC\\ORIGINAL_MUSIC','C:\\MUSIC\\ORIGINAL_MUSIC','G:\\MUSIC\\MP3_COLLECTION','C:\\MUSIC\\MP3_COLLECTION']
	dirAllL =  []
	cfgD = myMediaLib_adm.readConfigData(mymedialib_cfg)
	
	logger = logging.getLogger('dispatcher_logger')
	logger.setLevel(logging.INFO)
	# create file handler which logs even debug messages
		
	logPath='no Path'
		
	try:
		logPath=cfgD['logPath']
	except Exception,e:
		print e
			
		
	fh = logging.FileHandler(logPath)
	fh.setLevel(logging.INFO)
		# create console handler with a higher log level
	ch = logging.StreamHandler()
	ch.setLevel(logging.CRITICAL)
		
		# create formatter and add it to the handlers
	formatter = logging.Formatter('%(asctime)s - %(name)25s - %(levelname)s - %(message)50s')
	ch.setFormatter(formatter)
	fh.setFormatter(formatter)
		
	logger.addHandler(ch)
	logger.addHandler(fh)
	
	
	if 'audio_files_path_list' in cfgD:
		dirAllL = cfgD['audio_files_path_list']
		print 'Following path used:'
		print '\n'.join(dirAllL)
	else:
		print "please maintain in config 'audio_files_path_list like ---> audio_files_path_list = C:\MUSIC\ORIGINAL_MUSIC; G:\MUSIC\MP3_COLLECTION;"
		return 0
	dbPath = cfgD['dbPath']	
	
	while 1:
		param = ''
		start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
		time.sleep(10)
		print 'Running:',start_time, ' --->',
		l = myMediaLib_adm.get_Tasks_in_queue(dbPath)
		if l <> []:
			logger.info(" Task dispatcher cought new task:"+str(l[0]))
			if l[0][1] == str('update_lib'):
				print 'Got new:',l[0]
				res = myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'run_task')
				resDBS = myMediaLib_adm.mediaLib_intoDb_Load_withUpdateCheck(dbPath,dirAllL,None,'save_db')
				
				
				myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'finish_task')
				print 'Task finished',l[0]
				logger.info("Task dispatcher 53 finished task:"+str(l[0]))
				
			elif l[0][1] == str('update_lib_cur_dir'):
				print 'Got new:',l[0]
				res = myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'run_task')
				print res[5]
				
				if res[5] <> None:
					curDirL = [res[5]]
					resDBS = myMediaLib_adm.mediaLib_intoDb_Load_withUpdateCheck(dbPath,curDirL,None,'save_db')
					#resDBS = myMediaLib_adm.mediaLib_intoDb_Load_withUpdateCheck(dbPath,curDirL,'save_db')
					myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'finish_task')
				print 'Task finished',l[0]
				logger.info("Task dispatcher 65 finished task:"+str(l[0]))
				
			elif l[0][1] == str('generate_ml_folder_tree_all'):
				print 'Got new:',l[0]
				res = myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'run_task')
				print res[5]
				
				if res[5] <> None:
					curDirL = [res[5]]
					resDBS = myMediaLib_tools.find_new_music_folder(dirAllL,[],{'resBuf_save':'resBuf_ml_folder_tree.dat','progress_db':l[0][0]})
					
					if 'resBuf_save' in resDBS:
						param = resDBS['resBuf_save']
					
					myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'finish_task')
				print 'Task finished',l[0]
				logger.info("Task dispatcher 121 finished task:"+str(l[0]))	
				
			elif l[0][1] == str('check_new_album_2_lib'):
				# Проверка и Подготовка альбома в спец папке для загрузки в библиотеку
				print 'Got new:',l[0]
				res = myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'run_task')
				print res[5]
				
				if res[5] <> None:
					# проверить новый альбом из специальной дирректории, разбить на трэки и получить fingerprint
					# в другом сценарии (закладка проверить альбом) получить метаданные, если все ок - назначить целевую папку-категорию 
					curDirL = [res[5]] 
					resDBS = myMediaLib_adm.mediaLib_intoDb_Load_withUpdateCheck(dbPath,curDirL,None,'save_db')
					myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'finish_task')
				print 'Task finished',l[0]
				logger.info("Task dispatcher 65 finished task:"+str(l[0]))	
			elif l[0][1] == str('del_missing_lib'):
				
				print 'Got new:',l[0]
				res = myMediaLib_adm.maintain_Task_for_event(dbPath,l[0][0],param,'run_task')
				r = myMediaLib_adm.collectMyMediaLib_folder_new(dirAllL,'stat')
				metaD = r['allmFD']
				myMediaLib_adm.remove_missing_fromDB(dbPath,metaD,dirAllL)
								
				maintain_Task_for_event(dbPath,l[0][0],param,'finish_task')
				print 'Task finished',l[0]
				logger.info("Task dispatcher 76 finished task:"+str(l[0]))
			else:
			
				print 'Unknown_task',l[0][1]
				logger.info("Task dispatcher 80 finished task unknown")
				
		else:
			print 'Task pool is empty'
	
	
if __name__ == '__main__':
	run_forever()