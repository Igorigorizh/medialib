import os
import xmlrpclib
from pprint import pformat
import json
import pickle

def application(environ, start_response):
	output = ['<pre>']
	output.append('If you see this - it is strange')
	output.append(['/<pre>'])
	output_len = sum(len(line) for line in output)
	response_headers = [('Content-type', 'text/plain'),
                    ('Content-Length', str(output_len))]
	s_appl = xmlrpclib.ServerProxy('http://127.0.0.1:9001')	
#	output = ['<pre>']
#	output.append(pformat(environ))
#	output.append('</pre>')
	
#	return output
	path = ''
	data = ''
	if '/cover' in environ['REQUEST_URI'] or 'no-image-availabl' in environ['REQUEST_URI']:
		pos = environ['REQUEST_URI'].find('/cover')+7	
		id= environ['REQUEST_URI'][pos:-4]
		#data = s_appl.get_image(id).data
		d = s_appl.get_image(id).data
		path = pickle.loads(os.path.normpath(d))
		
	elif '/album_images' in environ['REQUEST_URI']:
		pos = environ['REQUEST_URI'].find('/album_images')+14	
		pos_2 = environ['REQUEST_URI'].rfind('/')
						
		album_crc32= environ['REQUEST_URI'][pos:pos_2]
		image_crc32= environ['REQUEST_URI'][pos_2+1:]
		#data = s_appl.get_image("album_images",{'album_crc32':album_crc32,'image_crc32':image_crc32}).data
		d = s_appl.get_image("album_images",{'album_crc32':album_crc32,'image_crc32':image_crc32}).data
		
		path = pickle.loads(os.path.normpath(d))

	elif '/100_cover' in environ['REQUEST_URI'] or 'no-image-availabl' in environ['REQUEST_URI']:
		if '/100_cover' in environ['REQUEST_URI']:
			pos = environ['REQUEST_URI'].find('/100_cover')+11	
			id= environ['REQUEST_URI'][pos:]

		#data = s_appl.get_image('search_icon',id).data
		d = s_appl.get_image('search_icon',id).data
		
		path = pickle.loads(os.path.normpath(d))
		#path = u'Y:\\MUSIC\\Mozart - Last concertos - Staier, Coppola\\cover_320.jpg'
		#path = u'G:\\MUSIC\\'	
		#print 'path check:',os.path.exists(os.path.normpath(path)),os.path.normpath(path)
	# Conditions above are true	
	if path != '':
				
		if os.path.exists(path):
			fileObj = open(path,'rb')
			image = fileObj.read()
			fileObj.close()
			
			if '.pdf' in environ['REQUEST_URI'] and '.pdf' in path:
				response_headers = [('Content-type', 'application/pdf'),
					('Content-Length', str(len(image)))]
			else:
				response_headers = [('Content-type', 'image/jpeg'),
					('Content-Length', str(len(image)))]
			
			start_response('200 OK', response_headers)
			return [image]
		else:
			print 'Error in image.wsgi with image path:',[path]
			res = 'Wrong path returned in image.wsgi:'+str([path])
			#output.append(res)
			
			#output_len = sum(len(line) for line in output)
			output_len = len(res)
			
			response_headers = [('Content-type', 'text/plain'),
                    ('Content-Length', str(output_len))]
			
			start_response('400 Bad data', response_headers)
			
			return res
	
	controlL = ['play','stop','next','prev','pause']
	
	for command_name in controlL:
		if '/'+command_name+'.jpg' in environ['REQUEST_URI']:
			image = s_appl.get_control_pics(command_name).data
			response_headers = [('Content-type', 'image/jpeg'),
	        	('Content-Length', str(len(data))),
			('Cache-Control','private')]				
			start_response('200 OK', response_headers)
			return [image]
##		response_headers = [('Content-type', 'image/jpeg'),
##	        	('Content-Length', str(len(data))),
##			('Cache-Control','private')]
	
	start_response('400 OK', response_headers)
	
	return [data]
##	return output