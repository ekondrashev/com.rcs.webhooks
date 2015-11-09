#!/usr/bin/python

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import cgi
import json
import sys
import os
import subprocess
import time
import getpass
import smtplib
from os.path import basename
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
import shlex
from sys import stdout

_author__ = "Eugene Kondrashev"
__copyright__ = "Copyright 2015, Eugene Kondrashev"
__credits__ = ["Eugene Kondrashev"]
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Eugene Kondrashev"
__email__ = "eugene.kondrashev@gmail.com"
__status__ = "Prototype"

PORT_NUMBER = 8181
# parser = argparse.ArgumentParser()
# parser.add_argument("user")
# parser.add_argument("pass")
# parser.add_argument("to")


def send(username, password, tousr, subj, body, files=None):
	msg = MIMEMultipart(
        From=username,
        To=COMMASPACE.join(tousr),
        Date=formatdate(localtime=True),
    )
	msg.attach(MIMEText(body))
	msg['Subject'] = subj

	for f in files or []:
		with open(f, "rb") as fil:
			msg.attach(MIMEApplication(
				fil.read(),
                Content_Disposition='attachment; filename="%s"' % basename(f),
                Name=basename(f)
            ))

#     headers = "\r\n".join(["from: " + username,
#                        "subject: " + subj,
#                        "to: " + tousr,
#                        "mime-version: 1.0",
#                        "content-type: text/html"])
#
#     # body_of_email can be plaintext or html!
#     content = headers + "\r\n\r\n" + body
#     import smtplib

	# The below code never changes, though obviously those variables need values.
	session = smtplib.SMTP('smtp.gmail.com', 587)
	session.ehlo()
	session.starttls()
	session.login(username, password)
	session.sendmail(username, tousr, msg.as_string())

def authors(form):
	result = set()
	for commit in form['commits']:
		result.add(commit['author']['email'])
	return result

def rebuild(path):
	print path
	log = '%s.txt' % (os.path.join(
		'/tmp', str(int(round(time.time() * 1000)))
	))
	print 'Log: %s' % log
	with open(log, 'w') as logfile:
		pull = subprocess.Popen(
			shlex.split('git pull --rebase'),
			cwd=path,
			stdout=logfile,
			stderr=logfile
		)
		pull.wait()
		print pull.returncode
		if pull.returncode == 0:
			build = subprocess.Popen(
				shlex.split('mvn clean install'),
				cwd=path,
				stdout=logfile,
				stderr=logfile
			)
			build.wait()
			return build.returncode == 0, log
	return None, log

def handler(path, username, password):
	class Handler(BaseHTTPRequestHandler):

		#Handler for the POST requests
		def do_POST(self):
			if self.path=="/push":
				form = cgi.FieldStorage(
					fp=self.rfile,
					headers=self.headers,
					environ={'REQUEST_METHOD':'POST',
			                 'CONTENT_TYPE':self.headers['Content-Type'],
				})
				body = json.loads(form.value)
				print body['ref']
				if body['ref'] == 'refs/heads/master':
					print "Form: %s" % form
					self.send_response(200)
					self.end_headers()
					self.wfile.write("Thanks !")
					subj, msg = '', ''
					succeeded, log = rebuild(path)
					if succeeded:
						subj, msg = 'Build status: Ok', 'Cool'
					else:
						subj, msg = 'Build status: Failed', 'Not cool'
					send(username, password, authors(body), subj, msg, [log,])
					return
	return Handler


if len(sys.argv) < 2:
	print "Invalid path to build project and mail account name"
else:
	try:
		#Create a web server and define the handler to manage the
		#incoming request
		server = HTTPServer(('', PORT_NUMBER), handler(sys.argv[1], sys.argv[2], getpass.getpass()))
		print 'Started httpserver on port ' , PORT_NUMBER

		#Wait forever for incoming htto requests
		server.serve_forever()

	except KeyboardInterrupt:
		print '^C received, shutting down the web server'
		server.socket.close()
