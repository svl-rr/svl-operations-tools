#!/usr/bin/python

# somewhat hacky conversion of SVL XML file into a hash of hashes for quick and easy data access

from xml.dom.minidom import parseString, Node

def importXML():
 
  #open the xml file for reading:
  file = open('SVL_Base_sess_post.xml','r')
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
