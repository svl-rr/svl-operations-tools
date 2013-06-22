#!/usr/bin/python

import extract

cars = extract.importXML()
extract.importNowheresYCRA(cars)
extract.importBayshoreYCRA(cars)
