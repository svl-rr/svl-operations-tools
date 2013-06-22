#!/usr/bin/python

# somewhat hacky conversion of SVL XML file into a hash of hashes for quick and easy data access

from xml.dom.minidom import parseString, Node

import re

def importXML(filename='SVL_Base_sess_post.xml'):
 
  #open the xml file for reading:
  file = open(filename,'r')
  #convert to string:
  data = file.read()
  #close file because we dont need it anymore:
  file.close()
  #parse the xml you got from the file
  dom = parseString(data)

  dom_switchster = dom.getElementsByTagName('SWITCHSTER_XML')[0]
  version = {}
  version['created'] = dom_switchster.getElementsByTagName('PlatformInfo')[0].getAttribute('dateCreated')
  version['session'] = dom_switchster.getElementsByTagName('OpsHLD')[0].getAttribute('lastSessionID')
  version['car_number'] = 'none'
  
  blocks = {}
  dom_blocks = dom_switchster.getElementsByTagName('LayoutHLD')[0].getElementsByTagName('Block')
  print dom_blocks
  for dom_block in dom_blocks:
    id = dom_block.getAttribute('id')
    name = dom_block.childNodes[0].data
    blocks[id] = name
    print id,name

  dom_locations = dom_switchster.getElementsByTagName('LayoutLLD')[0].childNodes
  locations={}
  for dom_location in dom_locations:
    if dom_location.nodeType == Node.TEXT_NODE:
      continue
    id = dom_location.getAttribute('id')
    block = dom_location.getAttribute('block')
    name = [blocks[block], dom_location.childNodes[0].data]
    locations[id] = name

  dom_carDatabase = dom_switchster.getElementsByTagName('CarDatabase')[0]
  dom_cars = dom_carDatabase.getElementsByTagName('Car')
  cars={}
  for dom_car in dom_cars:
    fields = dom_car.getAttribute('fields')
    id = dom_car.getAttribute('id')
    props = fields.split(',')
    CarNumber = props[1]
    ReportingMark = props[2]
    cars[id] = {'car_number': ReportingMark + ' ' + CarNumber}

  dom_opsCars = dom_switchster.getElementsByTagName('OpsCars')[0]
  dom_cars = dom_opsCars.getElementsByTagName('Car')
  for dom_car in dom_cars:
    id = dom_car.getAttribute('id')
    location = dom_car.getAttribute('location')
    dom_tripPlans = dom_car.getElementsByTagName('CarTripPlan')
    if 'Location' not in cars[id]:
      cars[id]['Location'] = []
      cars[id]['Dst'] = []
      cars[id]['Phase'] = []
      cars[id]['Rcvr'] = []
      cars[id]['Shipper'] = []
    if location in locations:
      cars[id]['Location'] = locations[location]
    else:
      cars[id]['Location'] = 'unknown'
    if len(dom_tripPlans) > 0:
      dom_tripPlan = dom_tripPlans[0]
      phase = dom_tripPlan.getAttribute('phase')
      phaseDest = dom_tripPlan.getAttribute('phaseDest')
      rcvr = dom_tripPlan.getAttribute('rcvr')
      shipper = dom_tripPlan.getAttribute('shipper')
      cars[id]['Dst'].append(locations[phaseDest])
      cars[id]['Phase'].append(phase)
      if rcvr in locations:
        cars[id]['Rcvr'].append(locations[rcvr])
      if shipper in locations:
        cars[id]['Shipper'].append(locations[shipper])

  dom_scheduledTrains = dom_switchster.getElementsByTagName('OpsScheduledTrains')[0]
  dom_trainSchedules = dom_scheduledTrains.getElementsByTagName('TrainSchedule')
  trains = {}
  for dom_train in dom_trainSchedules:
    id = dom_train.getAttribute('id')
    symbol = dom_train.getAttribute('symbol')
    dom_first_station = dom_train.getElementsByTagName('Route')[0].getElementsByTagName('Station')[0]
    if id not in trains:
	trains[id] = {}
    trains[id]['Symbol'] = symbol
    trains[id]['DepTime'] = dom_first_station.getAttribute('depTime')
 

  dom_pendingTrains = dom_switchster.getElementsByTagName('OpsPendingTrains')[0].getElementsByTagName('PendingTrain')
  for dom_train in dom_pendingTrains:
    id = dom_train.getAttribute('id').split('|')[1][:-1]
    if id not in trains:
      train = 'unknown'
      depTime = '--:--:--'
    else:
      train = trains[id]['Symbol']
      depTime = trains[id]['DepTime']
    for move in dom_train.getElementsByTagName('PlannedCarMovement'):
      carID = move.getAttribute('carID')  
      endLoc = move.getAttribute('endLoc')
      if endLoc not in locations:
        endLoc = ''
      else:
        endLoc = locations[endLoc]
      endBlock = move.getAttribute('endRPBlockID')
      if endBlock not in blocks:
        endBlock = ''
      else:
        endBlock = blocks[endBlock]
      startLoc = move.getAttribute('startLoc')
      if startLoc not in locations:
        startLoc = ''
      else:
        startLoc = locations[startLoc]
      startBlock = move.getAttribute('startRPBlocID')
      if startBlock not in blocks:
        startBlock = ''
      else:
        startBlock = blocks[startBlock]
      if 'Move' not in cars[carID]:
        cars[carID]['Move'] = []
      cars[carID]['Move'].append(
	{'symbol': train, 'depTime' : depTime, 
         'startBlock' : startBlock, 'startLoc' : startLoc, 
         'endBlock' : endBlock, 'endLoc' : endLoc }
      )

  cars['version'] = version

  return cars

def importNowheresYCRA(cars, filename='YCR-A-Nowheres Yard.html'):
  importYCRA(cars, filename, 'Nowheres')

def importBayshoreYCRA(cars, filename='YCR-A-Bayshore Yard.html'):
  importYCRA(cars, filename, 'Bayshore')

def importYCRA(cars, filename, yardname):

  #open the ycra file for reading:
  file = open(filename,'r')
  #convert to string:
  data = file.read()
  #close file because we dont need it anymore:
  file.close()

  # I hate parsing data out of html. especially if the html is invalid xml.

  # Basic checks:
  # - we actually have a Nowheres YCRA report
  # - session matches session in cars
  m = re.search('<title>%s Yard Yardmaster Car Report \(All\)</title>' % yardname, data)
  if not m:
    print 'This is not a %s YCRA report' % yardname
    return False

  m = re.search('Report for session: (\d+)', data)
  if not m:
    print 'No session information found'
    return False
  session = m.group(1)
  if session != cars['version']['session']:
    print 'Session mismatch: >%s< from YCRA, >%s< from XML' % (session, cars['version']['session'])
    return False

  # parse out all occurences of future train assignments
  # pattern:
  # <tr  BGCOLOR=""><td  align="center"></td><td  align="center">Nowheres&nbsp;Yard</td><td  align="center">ATSF&nbsp;135506</td><td  align="center">XM4</td><td  align="center">Empty</td><td  align="center">Jasper&nbsp;Jct.&nbsp;|&nbsp;Jasper&nbsp;Track&nbsp;#5&nbsp;-&nbsp;Old&nbsp;Junction&nbsp;City&nbsp;(5,6)</td><td  align="center">378|57</td><td  align="center"><input type="checkbox" name="TASK_COMPLETE" value="OFF" /></td></tr>
  p = '<tr.*<td.*>%s&nbsp;Yard</td><td.*>(.*)</td><td.*/td><td.*/td><td .*>(.*)</td><td.*>(\d+\|\d+)</td><td.*td></tr>' % yardname
  cl = re.findall(p, data)
  future_cars = {}
  for c in cl:
    # c[car number, final destination, future train]
    car = c[0].replace('&nbsp;', ' ')
    final_dest = c[1].replace('&nbsp;', ' ')
    future_train = c[2]
    future_cars[car] = (car, final_dest, future_train)
  
  found_cars = {}
  # loop over known car numbers and find our cars
  for carid in cars.keys():
    if cars[carid]['car_number'] in future_cars:
      found_cars[carid] = future_cars[cars[carid]['car_number']]
      del future_cars[cars[carid]['car_number']]

  if len(future_cars) != 0:
    print 'Not all future cars were found in cars database'

  for carID in found_cars.keys():
    # plug those cars into the cars database
    if 'Move' not in cars[carID]:
      cars[carID]['Move'] = []
    cars[carID]['Move'].append(
        {'symbol': found_cars[carID][2], 'depTime' : '??:??:??',
         'startBlock' : yardname, 'startLoc' : [yardname, yardname + ' Yard'],
         'endBlock' : yardname, 'endLoc' : [yardname, 'assign to ' + found_cars[carID][2]] }
    )
  return True 

#cars = importXML()
#for car in cars:
#  print car,cars[car]
#  if 'Move' not in cars[car]:
#    move = None
#  else:
#    move = cars[car]['Move']
#  if 'Dst' not in cars[car]:
#    dst = None
#  else:
#    dst = cars[car]['Dst']
#  print cars[car]['car_number'],move,dst


#for location in locations:
#  print location,locations[location]
  
#car0 = cars[0].attributes
#i=0
#while i<car0.length:
#  print i,':  ',car0.item(i).value
#  i+=1


#retrieve the first xml tag (<tag>data</tag>) that the parser finds with name tagName:
#xmlTag = dom.getElementsByTagName('tagName')[0].toxml()
#strip off the tag (<tag>data</tag>  --->   data):
#xmlData=xmlTag.replace('<tagName>','').replace('</tagName>','')
#print out the xml tag and data in this format: <tag>data</tag>
#print xmlTag
#just print the data
#print xmlData
