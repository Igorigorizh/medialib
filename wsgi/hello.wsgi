# # -*- coding: cp1251 -*-
#-*- coding: utf-8 -*-
from pprint import pformat
import xmlrpclib,socket
import string,cgi,time
from urlparse import urlparse
from cgi import parse_qs
import time
import json
import os, sys
from subprocess import Popen

import winamp
sys.path.append(u'C:\\My_projects\\MyMediaLib')

#import myMediaLib_controller
from myMediaLib_adm import checkANDkillMLPids
from myMediaLib_adm import RebootServer
from myMediaLib_adm import loadTemplates_viaCFG
from myMediaLib_adm import readConfigData

mymedialib_cfg = u'C:\\My_projects\\MyMediaLib\\mymedialib.cfg'
#from myMediaLib_adm import getHardWareInfo

def getHardWareInfo():
	cpu_info_keyL = ['ProcessorId','ProcessorType','CurrentClockSpeed','Manufacturer','Name','CurrentVoltage','NumberOfCores','Caption','Family','SystemName']
	import subprocess
	import pythoncom
	import wmi
	pythoncom.CoInitialize()

	try:
		w = wmi.WMI(namespace="root\wmi")
	except wmi.x_access_denied, e:
		return 'error after w = wmi.WMI:'+str(e)
	except wmi.x_wmi_invalid_query, e:
		return 'error after w = wmi.WMI:'+str(e)
	except wmi.x_wmi_uninitialised_thread, e:
		return 'error after w = wmi.WMIwww:['+str(e)+']'

	try:
		temperature_info = w.MSAcpi_ThermalZoneTemperature()[0]
		res = 'System temperature:'+str(float(temperature_info.CurrentTemperature-2732)/10)
	except wmi.x_access_denied, e:
		return 'error after w = wmi.WMI:'+str(e)
	except wmi.x_wmi_invalid_query, e:
		return 'error after w = wmi.WMI:'+str(e)
	except wmi.x_wmi_uninitialised_thread, e:
		return 'error after w = wmi.WMIwww:['+str(e)+']'

	w = wmi.WMI(namespace="root\CIMV2")
	CPU_info = w.Win32_Processor()[0]


	for instance in CPU_info.properties:
		if instance in cpu_info_keyL:
			res+= '<BR>\n'+str(instance)+'-->'+str(getattr(CPU_info,instance))
	return res


def is_post_request(environ):
	if environ['REQUEST_METHOD'].upper() != 'POST':
		return False
	content_type = environ.get('CONTENT_TYPE', 'application/x-www-form-urlencoded')
	return (content_type.startswith('application/x-www-form-urlencoded')
		or content_type.startswith('multipart/form-data'))

def application(environ, start_response):
# ����� ������� ��������������� ������� �� ������� ����������
	if '/medialib' not in environ['REQUEST_URI']:
		exit
	
	p_appl = xmlrpclib.ServerProxy('http://127.0.0.1:9000')	
	s_appl = xmlrpclib.ServerProxy('http://127.0.0.1:9001')	
	try:
		request_body_size = int(environ.get('CONTENT_LENGTH', 0))
	except (ValueError):
		request_body_size = 0	
	output = ['']
	commandD = {}
	
	remote_addr = ''
	if 'REMOTE_ADDR' in environ:
		remote_addr = {'REMOTE_ADDR':environ['REMOTE_ADDR'],'HTTP_HOST':environ['HTTP_HOST']}
	
	
	command_routingD = {'/main':{'page_load':'main_page'},
						'/cast':{'page_load':'cast_page'},
						'/admin':{'page_load':'admin_page'},
						'/info':{'page_load':'info_page'},
						'/tagadmin':{'page_load':'tagAdmin_page'},
						'/search':{'page_load':'search_page'},
						'/trackpreload':{'page_load':'track_preload_page'},
						'/image':{'page_load':'image_page'},
						'/debug':{'page_load':'debug_page'},
						'/graf':{'page_load':'graf_page'},
						'/reports':{'page_load':'report_artist_page'},
						'/edit_artist':{'page_load':'edit_artist_page','artist':''}
						}
	
	if environ['REQUEST_METHOD'] == 'GET':	
	
		if '/main' in environ['REQUEST_URI']:
			commandD = command_routingD['/main']	
		elif '/admin' in environ['REQUEST_URI']:
			commandD = command_routingD['/admin']
		elif '/cast' in environ['REQUEST_URI']:
			commandD = command_routingD['/cast']	
		elif '/info' in environ['REQUEST_URI']:
			commandD = command_routingD['/info']
		elif '/search' in environ['REQUEST_URI']:
			commandD = command_routingD['/search']	
		elif '/image' in environ['REQUEST_URI']:
			commandD = command_routingD['/image']				
		elif '/trackpreload' in environ['REQUEST_URI']:
			commandD = command_routingD['/trackpreload']					
		elif '/graf' in environ['REQUEST_URI']:
			commandD = command_routingD['/graf']		
		elif '/debug' in environ['REQUEST_URI']:
			commandD = command_routingD['/debug']
		elif '/rappl' in environ['REQUEST_URI']:
			commandD = command_routingD['/debug']	
			
			Tmpl_D = {}
			configDict = readConfigData(mymedialib_cfg)
			try:
				for a in configDict['templatesD']:
					if  configDict['templatesD'][a]['active'] == True:
						Tmpl_D  = loadTemplates_viaCFG(configDict['templatesD'][a]['templatesPath'])
			except Exception,e:
				pass
				res = e
			page = Tmpl_D['restart_page']['TMPL']%({'host':environ['SERVER_ADDR']})	
			
			
			#page = res
			output.append(str(page))
			output_len = sum(len(line) for line in output)
			start_response('200 OK', [('Content-type', 'text/html'),
									  ('Content-Length', str(output_len))])
			return output					  
			
			
			pc = {}
			try:
				pc = p_appl.get_status()
				
				if 'playBack_Mode' in pc:
					res = 'Stopped at: '+str(pc['pl_pos'])+' from: '+str(pc['list_length'])
					p_appl.stop()
					output.append(res+'<BR>')
					
					r=p_appl.closeWinamp()
			except:
				output.append("No respond from player server..."+'<BR>')
			
			try:
				
				output.append('Restarting....'+'<BR>')
				

				RebootServer() 
				output.append('Done')
				
				#res = res + str(checkANDkillMLPids())
				
				
				output_len = sum(len(line) for line in output)
				start_response('200 OK', [('Content-type', 'text/html'),
									  ('Content-Length', str(output_len))])
				return output					  
			except:
				output.append(res)
				
		
		elif '/log' in environ['REQUEST_URI']:
			res = str(time.strftime('%X %x %Z'))+' <BR>   apache wsgi appl, player rpc, appl rpc to be tested.......... <BR> <BR> <BR>'
			if 'SERVER_ADDR' in environ:
				res += '1. apache wsgi-helloappl is OK: <BR>' + str('--------SERVER_ADDR') + '-->'+str(environ['SERVER_ADDR'])+"<BR>"
				output.append(res)
			
			
						
			res = '<BR> 2. apache wsgi-player: <BR>'
			try:		
				res = res + str(p_appl.get_status())
				res = res + '<BR> player is OK <BR>'
				output.append(res)
			except:
				res = res + 'player application failed!!! <BR>'
				output.append(res)
				
			# output_len = sum(len(line) for line in output)
			# start_response('200 OK', [('Content-type', 'text/html'),
									  # ('Content-Length', str(output_len))])	
			# return output
			
			
			res = '<BR> 3. apache wsgi-appl: <BR>'
			try:		
				res = res + str(s_appl.appl_status())
				res = res + '<BR> application instance is OK  <BR>'
				output.append(res)
			except:
				res = res + ' <BR> application controller instance failed!!!'
				output.append(res)
					
				
			res = '<BR> 4. apache wsgi appl log: <BR>'
			Tmpl_D = {}
			configDict = readConfigData(mymedialib_cfg)
			logPath='no Path'
			
			try:
				logPath=configDict['logPath']
				res = res + ' <BR>'
			except Exception,e:
				pass
				res = e

			#res = res+str(logPath)
			#res = str(configDict)

			color_template_red = "<span style='color:Red;background-color:Yellow'> %s '</span>'"	
			color_template_green = "<span style='color:Black;background-color:Cyan'> %s '</span>'"	
			color_template_orange = "<span style='color:Black;background-color:Orange'> %s '</span>'"	
			color_template_grey = "<span style='color:Black;background-color:Grey'> %s '</span>'"
			try:	
				logf = open(logPath,"r")
				lines = logf.readlines()
				logf.close()
		
				for i, a in enumerate(lines):
					if 'CRITICAL' in a:
						lines[i]= a.replace('CRITICAL', color_template_red%('CRITICAL'))
					elif 'DEBUG' in a:
						lines[i]= a.replace('DEBUG', color_template_green%('DEBUG'))			
					elif 'INFO' in a:
						lines[i]= a.replace('INFO', color_template_orange%('INFO'))			
					elif 'WARNING' in a:
						lines[i]= a.replace('WARNING', color_template_grey%('WARNING'))			

				lines.reverse()
				
			except Exception,e:
				pass
				res = str(e)
			
			
			try:		
				for a in lines[:150]:
					res = res + '<BR>'+a
				output.append(res)
			except:
				res = res + ' logging failed!!!'
				output.append(res)
				
			
			# except xmlrpclib.Fault, err:	
				# output.append("A fault occurred in status returning %s \n"%(str(''))
				# output.append("Fault code: %d \n" % err.faultCode)
				# output.append("Fault string: %s \n" % err.faultString)
			
			
			
			
			output_len = sum(len(line) for line in output)
			start_response('200 OK', [('Content-type', 'text/html'),
									  ('Content-Length', str(output_len))])
			return output					  
		
		elif '/mstat' in environ['REQUEST_URI']:
			
			res = str(time.strftime('%X %x %Z'))+' <BR>   apache wsgi appl, player rpc, appl rpc to be tested.......... <BR> <BR> <BR>'
			if 'SERVER_ADDR' in environ:
				res += '1. apache wsgi-helloappl is OK: <BR>' + str('--------SERVER_ADDR') + '-->'+str(environ['SERVER_ADDR'])+"<BR>"
				output.append(res)
			
			
						
			res = '<BR> 2. apache wsgi-player: <BR>'
			try:		
				res = res + str(p_appl.get_status())
				res = res + '<BR> player is OK <BR>'
				output.append(res)
			except:
				res = res + 'player application failed!!! <BR>'
				output.append(res)
				
			# output_len = sum(len(line) for line in output)
			# start_response('200 OK', [('Content-type', 'text/html'),
									  # ('Content-Length', str(output_len))])	
			# return output
			
			
			res = '<BR> 3. apache wsgi-appl: <BR>'
			try:		
				res = res + str(s_appl.appl_status())
				res = res + '<BR> application instance is OK  <BR>'
				output.append(res)
			except:
				res = res + ' <BR> application controller instance failed!!!'
				output.append(res)
					
				
					
			
			# except xmlrpclib.Fault, err:	
				# output.append("A fault occurred in status returning %s \n"%(str(''))
				# output.append("Fault code: %d \n" % err.faultCode)
				# output.append("Fault string: %s \n" % err.faultString)
			
			
			res = '<BR> 4. System hardware status: <BR>'
			try:
				res+= getHardWareInfo()
				output.append(res)
			except :
				output.append("error in getHardWareInfo:")
				
			res = '<BR> 5. ML services ranning: <BR>'	
			try:
				res+= str(checkANDkillMLPids())
				output.append(res)
			except :
				output.append("error in checkANDkillMLPids:")	
			
			output_len = sum(len(line) for line in output)
			start_response('200 OK', [('Content-type', 'text/html'),
									  ('Content-Length', str(output_len))])
			return output					  
					
			
			
			
					
		elif '/tagadmin' in environ['REQUEST_URI']:
			commandD = command_routingD['/tagadmin']	
		elif '/reports' in environ['REQUEST_URI']:
			commandD = command_routingD['/reports']	
		elif '/edit_artist' in environ['REQUEST_URI']:	
			dic = cgi.parse_qs(urlparse(environ['REQUEST_URI'])[4])
			if 'q' in dic:
				command_routingD['/edit_artist']['artist'] = dic['q'][0]
			commandD = command_routingD['/edit_artist']		
		
		#elif '/medialib' in environ['REQUEST_URI'] and 'search' not in environ['REQUEST_URI'] and '/environ' not in environ['REQUEST_URI']:
		#	commandD = command_routingD['/main']	
				
		elif '/environ' in environ['REQUEST_URI']:
			res = ''
			for a in environ:
				res = res + str(a) + '-->'+str(environ[a])+"<BR>"
			
			output.append(res)	
			output_len = sum(len(line) for line in output)
			start_response('200 OK', [('Content-type', 'text/html'),
								  ('Content-Length', str(output_len))])
					
			return output
			
		elif '/medialib' in environ['REQUEST_URI']:
			res = 'Empty medialib command <BR>'
			
			try:		
				res = res + str(p_appl.get_status())+'<BR>'
				
			except:
				res = res + 'player application failed!!! <BR>'
				
			try:		
				res = res + str(s_appl.appl_status())
			except:
				res = res + 'medialib application failed!!! <BR>'
				
				
			try:
				w=winamp.Winamp()
				pr_id = str(w._Winamp__processID)
				w_ver = str(w.getVersion())
				res = res +'<BR> Winamp live status:' + "<BR>"+'-->'+pr_id+ '<--'+ w_ver+"<BR>"
			except:
				res = res + '<BR> Winamp  failed!!! <BR>'	
				
			output.append(res)
			
			output_len = sum(len(line) for line in output)
			start_response('200 OK', [('Content-type', 'text/html'),
								  ('Content-Length', str(output_len))])
					
			return output	
			
			
		if commandD <> {}:	
			# ���������� ����������
			try:
				
				res = s_appl.command_dispatcher(commandD,remote_addr).data
			#output.append('Test page')
				if res <> 0:
					output.append(res)
				else:
					output.append('')
					
				output_len = sum(len(line) for line in output)
				start_response('200 OK', [('Content-type', 'text/html'),
								  ('Content-Length', str(output_len))])
					
				return output
				
			except xmlrpclib.Fault, err:	
				output.append("A fault occurred in new %s full page\n"%(str(commandD.values()[0])))
				output.append("Fault code: %d \n" % err.faultCode)
				output.append("Fault string: %s \n" % err.faultString)
				
			except socket.error, e:	
				output.append('Medialib Application Error:'+str(e)+'<BR>')
				output.append('*****************************************************<BR>')
				output.append('PLEASE CHECK IF MEDIALIB SERVICE IS RUNNING! <BR>')
				output.append('*****************************************************<BR>')
				
			except :
				output.append("A fault occurred new  FULL PAGE last--->\n %s"%(str(commandD.values()[0])))
				output.append("Unknown error" )
				
				
		commandD = {}		
		
        	
 #  ������� WSGI ���������� POST �������� ����� JSON
	if environ['REQUEST_METHOD'] == 'POST':
		if '/main' in environ['REQUEST_URI'] or '/edit_artist' in environ['REQUEST_URI'] or '/tagadmin' in environ['REQUEST_URI']  or '/admin' in environ['REQUEST_URI'] or '/search' in environ['REQUEST_URI'] or '/report' in environ['REQUEST_URI'] or '/graf' in environ['REQUEST_URI'] or '/cast' in environ['REQUEST_URI'] or '/debug' in environ['REQUEST_URI'] or '/image' in environ['REQUEST_URI'] or '/trackpreload' in environ['REQUEST_URI'] or '/start_ml' in environ['REQUEST_URI']:
			try:
				fs = get_post_form(environ)
			except :	
				output.append("A fault occurred form parsing--->\n %s")
				return output
			res = ''
			try:
				json_params = json.loads(fs)
			except :
				output.append("A fault occurred new main params parsing--->\n %s")
				return output	
				
			# ���������� ��� �������� � �������� ������ �� ������������ ��� ���������� ��������� �������	
			if 'do_admin' in json_params:
				if json_params['do_admin'] == 'restart_srv' or json_params['do_admin'] == 'shutdown_srv' or json_params['do_admin'] == 'remove_srv':
					if json_params['restart_pswrd'] == 'brumbul':
						
						if json_params['do_admin'] == 'restart_srv':
							reply = {"action_name": "do_admin", "action_result": 1,"message":'Rebooting'}
							output.append(json.dumps(reply))
							RebootServer() 
						if json_params['do_admin'] == 'shutdown_srv':	
							reply = {"action_name": "do_admin", "action_result": 1,"message":'Shutdowning... Take AC plug off and reloacate server'}
							output.append(json.dumps(reply))
							RebootServer(message='Shutdown', bReboot=0) 
						if json_params['do_admin'] == 'remove_srv':	
							reply = {"action_name": "do_admin", "action_result": 1,"message":'Removing ml services and Winamp... Restart services again'}
							output.append(json.dumps(reply))
							res = res + str(checkANDkillMLPids('kill')) 	
							output.append(res)
					else:
						reply = {"action_name": "do_admin", "action_result": 0,"message":'wrong password'}
						output.append(json.dumps(reply))
						
						
						
					output_len = sum(len(line) for line in output)
					start_response('200 OK', [('Content-type', 'text/html'),
								  ('Content-Length', str(output_len))])
					return output
					
			elif 'start_medialib'	in json_params:
			
				if json_params['start_medialib'] == 'start_player_controller':
					reply = {"action_name": "start_medialib", "action_result": 1,"message":'Starting...  please wait'}
					
					r = os.spawnve(os.P_WAIT, 'c:\Python27\python.exe', ['c:\Python27\python.exe','C:\My_projects\MyMediaLib\_player_server.py'], os.environ)
					
					output.append(json.dumps(reply))
				
				elif json_params['start_medialib'] == 'start_appl_controller':
					reply = {"action_name": "start_medialib", "action_result": 1,"message":'Starting...  please wait'}
					r = os.spawnve(os.P_WAIT, 'c:\Python27\python.exe', ['c:\Python27\python.exe','C:\My_projects\MyMediaLib\_appl_server.py'], os.environ)
					output.append(json.dumps(reply))	
					
				elif json_params['start_medialib'] == 'start_task_dispatcher':
					reply = {"action_name": "start_medialib", "action_result": 1,"message":'Starting...  please wait'}
					r = os.spawnve(os.P_WAIT, 'c:\Python27\python.exe', ['c:\Python27\python.exe','C:\My_projects\MyMediaLib\_task_dispatcher.py'], os.environ)
					output.append(json.dumps(reply))		
				
					
				
				output_len = sum(len(line) for line in output)
				start_response('200 OK', [('Content-type', 'text/html'),('Content-Length', str(output_len))])
				return output
				
			try:
				res = s_appl.command_dispatcher(json_params,remote_addr)
				#output.append('Test page')
				if res <> 0:
					output.append(res)
				else:
					output.append('')
				
				output_len = sum(len(line) for line in output)
				start_response('200 OK', [('Content-type', 'text/html'),
								  ('Content-Length', str(output_len))])
				return output
				
			except xmlrpclib.Fault, err:	
				output.append("A fault occurred in new WSGI MAIN\n")
				output.append("Fault code: %d \n" % err.faultCode)
				output.append("Fault string: %s \n" % err.faultString)
			except :
				output.append("A fault occurred new main last--->\n %s"%str(fs))
				output.append("Unknown error" )
				
			output_len = sum(len(line) for line in output)
			start_response('200 OK', [('Content-type', 'text/html'),
                              ('Content-Length', str(output_len))])	
			return output
		elif  '/async' in environ['REQUEST_URI']:	
			fs = get_post_form(environ)
			res = ''
			try:
				# ������� ���������� ������
				cur_status = json.loads(fs)
			except :
				output.append("A fault occurred new main params parsing--->\n %s")
				return output	
			try:
				respond =  {}
				cnt_sec = 0 
				while cnt_sec < 60:
					cnt_sec+=1	
					res = p_appl.get_status()
					
										
					
					if cur_status['playBack_Mode'] <>  res['playBack_Mode']:
						respond['playBack_Mode'] = res['playBack_Mode']
						
					if cur_status['pL_CRC32'] <>  res['pL_CRC32']:
						respond['pL_CRC32']= res['pL_CRC32']
					elif cur_status['pl_pos'] <>  res['pl_pos']:	
						respond['pl_pos'] =res['pl_pos']
					
					#print abs(int(cur_status['playingTrack_pos']/1000) - int(res['playingTrack_pos']/1000)),
					#print int(cur_status['playingTrack_pos']/1000), int(res['playingTrack_pos']/1000)
					
					if abs(int(cur_status['playingTrack_pos']/1000) - int(res['playingTrack_pos']/1000)) >	3:
						#pass
						#print abs(int(cur_status['playingTrack_pos']/1000) - int(res['playingTrack_pos']/1000)),
						respond['playingTrack_pos'] =res['playingTrack_pos']
					if respond <> {}:
						respond['playingTrack_pos'] = res['playingTrack_pos']
						dum = s_appl.refresh_content('play_list_sync',res)	
						output.append(json.dumps({'async_respond':respond}))
						output_len = sum(len(line) for line in output)
						start_response('200 OK', [('Content-type', 'text/html'),
								  ('Content-Length', str(output_len))])
						return output
						
						
					time.sleep(1)	
					
					if cur_status['playBack_Mode'] == 1:
						cur_status['playingTrack_pos']+=1000
				#print 'okkk->',respond
				
				#output.append('Test page')
				
				output.append(json.dumps({'async_respond':'endoflive'}))
				
				
				output_len = sum(len(line) for line in output)
				start_response('200 OK', [('Content-type', 'text/html'),
								  ('Content-Length', str(output_len))])
				return output
				
			except xmlrpclib.Fault, err:	
				output.append("A fault occurred in ASYNC\n")
				output.append("Fault code: %d \n" % err.faultCode)
				output.append("Fault string: %s \n" % err.faultString)
			except :
				output.append("A fault occurred new ASYNC --->\n %s"%str(fs))
				output.append("Unknown error" )
				
			output_len = sum(len(line) for line in output)
			start_response('200 OK', [('Content-type', 'text/html'),
                              ('Content-Length', str(output_len))])	
			return output
			
	return output
	
	
def get_post_form(environ):
	assert is_post_request(environ)
	post_form = environ.get('wsgi.post_form')
	input = environ['wsgi.input']
	#f = open('ajax.txt','w')
	#res = input.read()
	#f.write(res)
	#f.close()
	post_form = environ.get('wsgi.post_form')
	if (post_form is not None
		and post_form[0] is input):
		#f = open('ajax.txt','w+')
		#res = post_form[2].read()
		#f.write(res)
		#f.close()
		return post_form[2]
	# This must be done to avoid a bug in cgi.FieldStorage
	environ.setdefault('QUERY_STRING', '')
	try:
		fs = cgi.FieldStorage(fp=input,
							environ=environ,
							keep_blank_values=1)
	except:
		res = input.read()
		return res
    #new_input = InputProcessed('')
    #post_form = (new_input, input, fs)
    #environ['wsgi.post_form'] = post_form
   # environ['wsgi.input'] = new_input
	return fs

class InputProcessed(object):
	def read(self, *args):
		raise EOFError('The wsgi.input stream has already been consumed')
	readline = readlines = __iter__ = read	