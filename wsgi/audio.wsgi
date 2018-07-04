import os
import xmlrpclib
from pprint import pformat

def application(environ, start_response):
	s_appl = xmlrpclib.ServerProxy('http://127.0.0.1:9001')	
	
#	output = ['<pre>']
#	output.append(pformat(environ))
#	output.append('</pre>')
#	output_len = sum(len(line) for line in output)
#	response_headers = [('Content-type', 'text/plain'),
#                    ('Content-Length', str(output_len))]
#	return output

	data = ''
	path = ''
	if '/audio/' in environ['REQUEST_URI'] :
		pos = environ['REQUEST_URI'].find('/audio')+7	
		crc32 = environ['REQUEST_URI'][pos:-4]
		format = environ['REQUEST_URI'][-3:]
		print crc32,format
		try:
			path = s_appl.get_audio(crc32,format)
		except xmlrpclib.Fault, err:	
				output.append("A fault occurred in audio [] \n"%(str(err)))
				start_response('200 OK', response_headers)
				return output
		if os.path.exists(path):
			fileObj = open(path,'rb')
			data = fileObj.read()
			fileObj.close()
		if '.mp3' in environ['REQUEST_URI']:
			response_headers = [('Content-type', 'audio/mp3'),
					('Content-Length', str(len(data)))]
		elif '.flac' in environ['REQUEST_URI']:
			response_headers = [('Content-type', 'audio/flac'),
					('Content-Length', str(len(data)))]			

		elif format.lower() == 'ogg':
			response_headers = [('Content-type', 'audio/ogg'),
	        	('Content-Length', str(len(data)))]
				
		
	
		start_response('200 OK', response_headers)
	
	return [data]
##	return output