#!/usr/bin/python

# serve the SVL XML database on a quick and easy to use web page

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import cgi
import re

import extract

PORT_NUMBER = 8000
TABLEHEADER = (
'<table border=0 id="results" width=900>'
)
TABLEROWHEADER = (
'<tr bgcolor=aaaaaa>'
'<td colspan=2>Car</td><td colspan=2>Final Destination</td>'
'</tr><tr bgcolor=aaaaaa>'
'<td>Time</td><td align=right><b>Train</b></td><td><b>From</b></td><td><b>To</b></td>'
'</tr>'
)

TABLEFOOTER = '</table>'

PAGE="""
<html>
<head><title>bla</title>
<script language="javascript">
function updateCarNumber(digit) {
  setCarNumber(document.getElementById('car_number').value + digit)
}
function setCarNumber(car_number) {
  document.getElementById('car_number').value = car_number 
  if (car_number.length > 0) {
    car_number = 'searching ' + car_number + ' ...'
  } else { 
    car_number = 'idle'
  }
  document.getElementById('car_numberfield').innerHTML = car_number 
  requestResults()
}
function makeHttpObject() {
  try {return new XMLHttpRequest();}
  catch (error) {}
  try {return new ActiveXObject("Msxml2.XMLHTTP");}
  catch (error) {}
  try {return new ActiveXObject("Microsoft.XMLHTTP");}
  catch (error) {}
  throw new Error("Could not create HTTP request object.");
}
function requestResults() {
  var car_number = document.getElementById('car_number').value
  if (car_number == 'undefined') {
    car_number = ''
  }
  var request = makeHttpObject();
  request.open("GET", "/resultseval?car_number=" + car_number, true);
  request.send(null);
  request.onreadystatechange = function() {
    if (request.readyState == 4) {
      if (request.status == 200)
        updateResults(request.responseText);
    }
  };
}
function updateResults(response) {
  document.getElementById('results').innerHTML = response
}
</script>
</head>
<body>
<form action="/results" method=post id="selector">
<input type=hidden name="car_number" value="%(car_number)s" id='car_number' onchange="requestResults()">
<table width=900><tr>
<td width=300 height=60 bgcolor=dddddd fgcolor=white align=center valign=middle onclick="updateCarNumber('1')">1</td>
<td width=300 bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('2')">2</td>
<td width=300 bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('3')">3</td>
</tr><tr>
<td height=60 bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('4')">4</td>
<td bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('5')">5</td>
<td bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('6')">6</td>
</tr><tr>
<td height=60 bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('7')">7</td>
<td bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('8')">8</td>
<td bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('9')">9</td>
</tr><tr>
<td id='car_numberfield'></td>
<td height=60 bgcolor=dddddd align=center valign=middle onclick="updateCarNumber('0')">0</td>
<td bgcolor=aaaaaa align=center valign=middle onclick="setCarNumber('')">Clear</td>
</tr></table>
%(table_header)s
%(session)s
%(table_row_header)s
%(car_rows)s
%(table_footer)s
</form>
</body>
</html>
"""

filetypes = [
  ['.html', 'text/html'],
  ['.jpg', 'image/jpg'],
  ['.gif', 'image/gif'],
  ['.js', '.application/javascript'],
  ['.css', 'text/css'],
]

# dict of dicts holding car by car routing information
cars = {}

# format information about session as defined in cars
def GetSessionInfo():
  if 'version' in cars:
    return (
      '<tr><td colspan=2>Session: %s</td>'
      '<td colspan=2 align=right>Created: %s</td></tr>'
    ) % (
      cars['version']['session'],
      cars['version']['created']
    )
  else:
    return ''

#This class handles any incoming request from
#the browser
class svlHandler(BaseHTTPRequestHandler):

  #Handler for the GET requests
  def do_GET(self):
    if self.path=="/":
      # just send the empty template 
      self.send_response(200)
      self.send_header('Content-type','text/html')
      self.end_headers()
      self.wfile.write(
        PAGE % {
          'car_number' : '',
          'car_rows' : '',
          'table_header' : TABLEHEADER,
          'session' : GetSessionInfo(),
          'table_row_header' : TABLEROWHEADER,
          'table_footer' : TABLEFOOTER,
        } 
      )
      return

    if self.path.startswith('/resultseval'):
      # do a car lookup and return new raw results set
      self.send_response(200)
      self.end_headers()
      form = cgi.parse_qs(self.path[self.path.index('?') + 1:])
      print 'form',form
      self.wfile.write(self.HandleResultsEval(form))
      return

    # otherwise try serving a static page
    try:
      f = open(curdir + sep + self.path) 
      mimetype = ''
      for (ext, type) in filetypes:
        if self.path.endswith(ext):
          mimetype = type
      if mimetype:
        self.send_response(200)
        self.send_header('Content-type',mimetype)
        self.end_headers()
        self.wfile.write(f.read())
        f.close()
      else:
        # pretend we don't know what they are talking about
        print 'invalid file type requested'
        self.send_error(404, 'File Not Found: %s' % self.path) 
    except IOError:
      # Can't open or read the file
      self.send_error(404,'File Not Found: %s' % self.path)

  def do_POST(self):
    form = cgi.FieldStorage(
      fp=self.rfile, 
      headers=self.headers,
      environ={
        'REQUEST_METHOD':'POST',
        'CONTENT_TYPE':self.headers['Content-Type'],
      }
    )
    self.send_response(200)
    self.end_headers()
    fields = {}

    if self.path=='/upload':
      # new svl data file coming in.
      fields = self.HandleUpload(form)

    print 'using',fields
    try:
      self.wfile.write(PAGE % fields)
    except KeyError,e:
      print 'failed: %s' % e 
    return


  # handle upload of xml SVL file 
  def HandleUpload(self, form):
    print 'handling upload'

  # find all cars matching the provided partial car_number
  # returns formatted <td> rows 
  #  car_number: string to match car numbers for
  #  limit: maximum number of results requested
  def GetCarRows(self, car_number, limit):
    if len(car_number) == 0:
      return []

    p = re.compile('.*%s.*' % car_number)
    car_rows = []
    found = False
    for car in cars:
      if len(car_rows) > limit:
        return ['<tr><td>too many results</td></tr>']
      m = p.search(cars[car]['car_number'])
      if m:
        found = True
        print 'matched ',car
        print 'that is ',cars[car]
        if 'Move' in cars[car]:
          # this car is going on a train today.
          # move is array of dict with schedule info
          move = cars[car]['Move']
        else:
          move = []
        car_number = cars[car]['car_number']
        if 'Dst' in cars[car]:
          # car has a final destination
          dst = cars[car]['Dst']
          if len(dst) == 0:
            dst = [['','']]
        else:
          dst = [['', '']]

        # build table rows. first car information
        if len(move) > 0:
          car_number = '<b>%s</b>' % car_number
        car_row = (
          '<tr bgcolor=dddddd>'
          '<td colspan=2>%s</td>'
          '<td colspan=2><font color=999999>%s</font></td>'
          '</tr>'
        ) % (
          car_number,
          dst[0][0] + ' | ' + dst[0][1],
        )

        # now the train assignments. sort by departure time
        move.sort(key=lambda m: m['depTime'])		
        for m in move:
          car_row += ( 
            (
              '<tr><td bgcolor=dddddd>%s</td>'
              '<td align=right>%s</td>'
              '<td>%s</td>'
              '<td> --> %s</td>'
              '</tr>' 
            ) % (
              m['depTime'], m['symbol'],
              m['startLoc'][0] + ' | ' + m['startLoc'][1],
              m['endLoc'][0] + ' | ' + m['endLoc'][1],
            )
          )
        car_rows.append(car_row)

    if not found:
      car_rows.append('<tr><td>no results</td></tr>')
    return car_rows

  # format information about session
  def GetSessionInfo(self):
    if 'version' in cars:
      return (
        '<tr><td colspan=2>Session: %s</td>'
        '<td colspan=2 align=right>Created: %s</td></tr>'
      ) % (
        cars['version']['session'],
        cars['version']['created']
      )
    else:
      return ''

  # called by Javascript code. returns formatted table with results.
  def HandleResultsEval(self, form):
    print 'handling results eval'
    table = TABLEHEADER
    table += self.GetSessionInfo()
    table += TABLEROWHEADER
    if 'car_number' in form:
      car_rows = self.GetCarRows(form['car_number'][0], 10)
      table += ''.join(car_rows)
    table += TABLEFOOTER
    return table
		
			
try:
  # get data
  cars = extract.importXML()
  print cars
  #Create a web server and define the handler to manage the
  #incoming request
  server = HTTPServer(('', PORT_NUMBER), svlHandler)
  print 'Started httpserver on port ' , PORT_NUMBER

  #Wait forever for incoming htto requests
  server.serve_forever()

except KeyboardInterrupt:
  print '^C received, shutting down the web server'
  server.socket.close()
