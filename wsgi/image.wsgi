import os
import xmlrpclib
from pprint import pformat
import json
import pickle

def application(environ, start_response):
	s_appl = xmlrpclib.ServerProxy('http://127.0.0.1:9001')	
#	output = ['<pre>']
#	output.append(pformat(environ))
#	output.append('</pre>')
#	output_len = sum(len(line) for line in output)
#	response_headers = [('Content-type', 'text/plain'),
#                    ('Content-Length', str(output_len))]
#	return output
	path = ''
	data = ''
	if '/cover' in environ['REQUEST_URI'] or 'no-image-availabl' in environ['REQUEST_URI']:
		pos = environ['REQUEST_URI'].find('/cover')+7	
		id= environ['REQUEST_URI'][pos:-4]
		#data = s_appl.get_image(id).data
		d = s_appl.get_image(id).data
		path = pickle.loads(d)
		
	elif '/album_images' in environ['REQUEST_URI']:
		pos = environ['REQUEST_URI'].find('/album_images')+14	
		pos_2 = environ['REQUEST_URI'].rfind('/')
						
		album_crc32= environ['REQUEST_URI'][pos:pos_2]
		image_crc32= environ['REQUEST_URI'][pos_2+1:]
		#data = s_appl.get_image("album_images",{'album_crc32':album_crc32,'image_crc32':image_crc32}).data
		d = s_appl.get_image("album_images",{'album_crc32':album_crc32,'image_crc32':image_crc32}).data
		
		path = pickle.loads(d)

	elif '/100_cover' in environ['REQUEST_URI'] or 'no-image-availabl' in environ['REQUEST_URI']:
		if '/100_cover' in environ['REQUEST_URI']:
			pos = environ['REQUEST_URI'].find('/100_cover')+11	
			id= environ['REQUEST_URI'][pos:]

		#data = s_appl.get_image('search_icon',id).data
		d = s_appl.get_image('search_icon',id).data
		path = pickle.loads(d)
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