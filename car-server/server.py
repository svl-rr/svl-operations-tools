#!/usr/bin/python

# serve the SVL XML database on a quick and easy to use web page

from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import cgi
import os
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
<head><title>Car Lookup</title>
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
  var switchlist_id = document.getElementById('switchlist_id').value
  if (car_number == 'undefined') {
    car_number = ''
  }
  var request = makeHttpObject();
  request.open("GET", "/resultseval?car_number=" + car_number + "&sid=" + switchlist_id, true);
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
function SLMSetId() {
  var switchlist_id = document.getElementById('switchlist_id').value;
  if (switchlist_id.length > 0) {
    document.getElementById('switchlist_href').href = '/switchlist_print?sid=' + switchlist_id;
    SLMAddCar('')
    requestResults()
  }
}
function SLMAddCar(car) {
  var switchlist_id = document.getElementById('switchlist_id').value;
  if (switchlist_id.length > 0) {
    var request = makeHttpObject();
    request.open("GET", "/switchlist_add?car=" + car + "&sid=" + switchlist_id, true);
    request.send(null);
    request.onreadystatechange = function() {
      if (request.readyState == 4) {
        if (request.status == 200) {
          SLMUpdateCount(request.responseText);
        }
      }
    }
  }
}
function SLMUpdateCount(response) {
  document.getElementById('switchlist_len').innerHTML = response + " cars"
  setCarNumber('')
}

</script>
</head>
<body>
<div align=right><a href="/upload.html">Upload</a></div>
<form action="/results" method=post id="selector">
<input type=hidden name="car_number" value="%(car_number)s" id="car_number" onchange="requestResults()">
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
<br><br>
</form>
<div align=right>
Switch&nbsp;List:<br>
<input type=text name="switchlist_id" id="switchlist_id" onchange="SLMSetId()">
<a href="/switchlist_print" target="slmp" id="switchlist_href"><div id="switchlist_len">0 cars</div></a>
</div>
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

# dict of switch list arrays
switchlists = {}

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

  def sendEmptyTemplate(self):
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

  #Handler for the GET requests
  def do_GET(self):
    if self.path=="/":
      self.sendEmptyTemplate()
      return

    if self.path.startswith('/resultseval'):
      # do a car lookup and return new raw results set
      self.send_response(200)
      self.end_headers()
      form = cgi.parse_qs(self.path[self.path.index('?') + 1:])
      print 'form',form
      self.wfile.write(self.HandleResultsEval(form))
      return

    if self.path.startswith('/switchlist_add'):
      # add selected car to switchlist
      self.send_response(200)
      self.end_headers()
      form = cgi.parse_qs(self.path[self.path.index('?') + 1:])
      print 'form',form
      self.wfile.write(self.HandleSwitchListAdd(form))
      return

    if self.path.startswith('/switchlist_print'):
      # print switch list
      self.send_response(200)
      self.end_headers()
      form = cgi.parse_qs(self.path[self.path.index('?') + 1:])
      print 'form',form
      self.wfile.write(self.HandleSwitchListPrint(form))
      return

    if self.path.startswith('/switchlist_delete'):
      # delete switch list
      self.send_response(200)
      self.end_headers()
      form = cgi.parse_qs(self.path[self.path.index('?') + 1:])
      print 'form',form
      self.wfile.write(self.HandleSwitchListDelete(form))
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
    if self.path in ['/results', '/']:
      print 'POST to /results or / . Returning empty template.'
      self.sendEmptyTemplate()
      return

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

    if self.path=='/handle_files':
      # new svl data file coming in.
      fields = self.HandleUpload(form)

    print 'using',fields
    try:
      self.wfile.write(PAGE % fields)
    except KeyError,e:
      print 'failed: %s' % e 
    return


  # handle upload of xml SVL file 
  # and Nowheres/Bayshore Yardmaster paperwork
  def HandleUpload(self, form):

    def SaveFile(formfile):
      if formfile.filename:
        fn1 = 'files/' + os.path.basename(formfile.filename)
        fn = fn1
        count = 0
        while os.path.exists(fn):
          fn = '%s-%d' % (fn1, count)
          count += 1
        f = open(fn, 'wb')
        f.write(formfile.file.read())
        f.close()
        print 'uploaded %s' % fn
        return fn
      return None

    xmlfile = form['xmlfile']
    nowheresfile = form['nowheresfile']
    bayshorefile = form['bayshorefile']

    data_valid = True
    xmlfilename = SaveFile(xmlfile)
    nowheresfilename = SaveFile(nowheresfile)
    bayshorefilename = SaveFile(bayshorefile)
    if xmlfilename:
      print 'XML upload success'
      new_cars = extract.importXML(xmlfilename)
      if new_cars:
        print 'XML import success'
      else:
        data_valid = False
    if nowheresfilename:
      print 'Nowheres upload success'
      if extract.importNowheresYCRA(new_cars, nowheresfilename):
        print 'Nowheres import success'
      else:
        data_valid = False
    if bayshorefilename:
      print 'Bayshore upload success'
      if extract.importBayshoreYCRA(new_cars, bayshorefilename):
        print 'Bayshore import success'
      else:
        data_valid = False
    if data_valid:
      try:
        os.unlink('SVL_Base_sess_post.xml')
      except: 
        pass
      try:
        os.unlink('YCR-A-Nowheres Yard.html')
      except:
        pass
      try:
        os.unlink('YCR-A-Bayshore Yard.html')
      except:
        pass
      os.symlink(xmlfilename, 'SVL_Base_sess_post.xml')
      print 'using new XML file'
      if nowheresfilename:
        os.symlink(nowheresfilename, 'YCR-A-Nowheres Yard.html')
        print 'using new Nowheres YCRA'
      if bayshorefilename:
        os.symlink(bayshorefilename, 'YCR-A-Bayshore Yard.html')
        print 'using new Bayshore YCRA'
      cars.update(new_cars)
    
    return {
          'car_number' : '',
          'car_rows' : '',
          'table_header' : TABLEHEADER,
          'session' : GetSessionInfo(),
          'table_row_header' : TABLEROWHEADER,
          'table_footer' : TABLEFOOTER,
        } 

  # look up and return car destination and moves
  def GetDstAndMove(self, car):
    dst = [['','']]
    move = []
    if 'Move' in cars[car]:
      # this car is going on a train today.
      # move is array of dict with schedule info
      move = cars[car]['Move']
      # sort by departure time
      move.sort(key=lambda m: m['depTime'])
    if 'Dst' in cars[car]:
      # car has a final destination
      dst = cars[car]['Dst']
      if len(dst) == 0:
        dst = [['','']]
    return (dst, move)

  # find all cars matching the provided partial car_number
  # returns formatted <td> rows 
  #  car_number: string to match car numbers for
  #  limit: maximum number of results requested
  def GetCarRows(self, form, limit):
    car_number = form['car_number'][0]
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
        car_number = cars[car]['car_number']
        (dst, move) = self.GetDstAndMove(car)

        print 'found', dst, move

        # build table rows. first car information
        if len(move) > 0:
          car_number = '<b>%s</b>' % car_number
            
        car_row = """
          <tr bgcolor=dddddd>
          <td colspan=2 onclick="SLMAddCar('%s')">%s</td>
          <td colspan=2 onclick="SLMAddCar('%s')"><font color=999999>%s</font></td>
          </tr>
        """ % (
          car, car_number,
          car, dst[0][0] + ' | ' + dst[0][1],
        )

        # now the train assignments.
        for m in move:
          car_row += ( 
            """
              <tr><td bgcolor=dddddd onclick="SLMAddCar('%s')">%s</td>
              <td align=right onclick="SLMAddCar('%s')">%s</td>
              <td onclick="SLMAddCar('%s')">%s</td>
              <td onclick="SLMAddCar('%s')"> --> %s</td>
              </tr>
            """ % (
              car, m['depTime'], 
              car, m['symbol'],
              car, m['startLoc'][0] + ' | ' + m['startLoc'][1],
              car, m['endLoc'][0] + ' | ' + m['endLoc'][1],
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
      car_rows = self.GetCarRows(form, 20)
      table += ''.join(car_rows)
    table += TABLEFOOTER
    return table

  # returns formatted table with switchlist content
  def HandleSwitchListPrint(self, form):
    print 'handling switchlist print'
    if not 'sid' in form:
      return 'no switchlist ID given'
    sid = form['sid'][0]
    if not sid in switchlists:
      return 'no switchlist with ID %s' %sid

    table = TABLEHEADER
    table += self.GetSessionInfo()
    table += TABLEROWHEADER
    for car in switchlists[sid]:
      car_number = cars[car]['car_number']
      (dst, move) = self.GetDstAndMove(car)

      print 'printing', dst, move

      # build table rows. first car information
      if len(move) > 0:
        car_number = '<b>%s</b>' % car_number

      table += """
        <tr bgcolor=dddddd>
        <td colspan=2>%s</td>
        <td colspan=2><font color=999999>%s</font></td>
        <td><input type=checkbox></td>
        </tr>
      """ % (
        car_number,
        dst[0][0] + ' | ' + dst[0][1],
      )

      # now the train assignments.
      for m in move:
        table += ( 
          """
            <tr><td bgcolor=dddddd>%s</td>
            <td align=right>%s</td>
            <td>%s</td>
            <td> --> %s</td>
            </tr>
          """ % (
            m['depTime'],
            m['symbol'],
            m['startLoc'][0] + ' | ' + m['startLoc'][1],
            m['endLoc'][0] + ' | ' + m['endLoc'][1],
          )
        )
    table += TABLEFOOTER
    
    table += """
      <br>
      <a href="/switchlist_delete?sid=%s">Delete Switch List</a>
    """ % sid
    
    return table

  def HandleSwitchListDelete(self, form):
    print 'handling switchlist delete'
    if not 'sid' in form:
      return 'no switchlist ID given'
    sid = form['sid'][0]
    if not sid in switchlists:
      return 'no switchlist with ID %s' % sid

    del switchlists[sid]
    return 'switchlist with ID %s deleted' % sid 

      

  # called by Javascript code. adds named car to switch list, 
  # returns current number of cars in switch list
  # if submitted car is '' just returns length of switchlist
  def HandleSwitchListAdd(self, form):
    print 'handling switchlist add'
    if 'sid' in form:
      sid = form['sid'][0]
      if 'car' in form:
        car = form['car'][0]
      else:
        car = ''
      if len(car) > 0:
        if not sid in switchlists: 
          switchlists[sid] = []
        found = False
        for slc in switchlists[sid]:
          if slc == car:
            found = True
            break
        if not found:
          switchlists[sid].append(car)
        print switchlists[sid]
      if sid in switchlists:
        return len(switchlists[sid])
    return 0
		
			
try:
  # get data
  cars = extract.importXML()
  extract.importNowheresYCRA(cars)
  extract.importBayshoreYCRA(cars)
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
