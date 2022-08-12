import pandas as pd
import plotly.express as px
import datetime
import numpy as np
import re
import copy, json, random

############################################################
##################### COURSE class #########################
############################################################
class Event:
    def __init__(self, eventCode, name, seats, capacity, maxCapacity, time, pastLocation, beginDate, endDate):
        self.eventCode = eventCode
        self.dept = getDept(eventCode)
        self.name = name
        self.seats = seats
        self.capacity = capacity
        self.maxCapacity = maxCapacity
        self.time = time
        self.beginDate = str(beginDate).split(" ")[0]
        self.endDate = str(endDate).split(" ")[0]
        self.indices = []   # keeps track of where the events are in the schedule
        self.__historicalLocations = [pastLocation]   # keeps track of the locations that the event was in the past
        self.bldgCode = pastLocation.split(" ")[0]
        self.roomNumber = pastLocation.split(" ")[1]
        self.placedLocation = ""
        self.metric = 0
        # self.requiredFeatures = requiredFeatures

    #########################################################################

    # Updates the indices to a new list of indices if there are no present indices
    def updateIndices(self, newIndices):
        if len(self.indices) != 0:
            return False
        self.indices = newIndices
        return True

    #########################################################################

    def updateHistoricalLocations(self, newHLocations):
        self.__historicalLocations = newHLocations

    #########################################################################

    def getHistoricalLocations(self):
        return self.__historicalLocations

    #########################################################################

    def info(self):
        return [self.eventCode, self.name, self.seats, self.time.info()]  # , self.requiredFeatures]

    #########################################################################


############################################################
##################### ROOM class ###########################
############################################################


class Location:
    def __init__(self, name, capacity, locationFeatures):
        self.name = name
        self.capacity = capacity
        self.locationFeatures = locationFeatures
        self.building = getDept(name)

    #########################################################################

    def info(self):
        return [self.name, self.capacity, self.locationFeatures]


############################################################
##################### TIME class ###########################
############################################################


class Time:
    def __init__(self, beginTime, endTime, days):
        self.beginTime = beginTime
        self.endTime = endTime
        self.totalTime = beginTime + " - " + endTime
        self.days = removeNans(days)

    #########################################################################

    def info(self):
        return [self.beginTime, self.endTime, self.days]

    #########################################################################


# takes in a list and returns a list with no nans
removeNans = lambda lst: [x for x in lst if str(x) not in ['nan', ' ']]


############################################################
################### SCHEDULE class #########################
############################################################

class Schedule:
    def __init__(self, locations, time=Time("6:00", "24:00", ['M', 'T', 'W', 'R']), interval=10, timeGap=10):
        self.schTime = time
        self.locations = locations
        self.interval = interval
        self.timeGap = timeGap

        self.dayInterval = int(60 / interval) * (int(str(subtractTime(self.schTime.beginTime, self.schTime.endTime)).split(":")[0]))  # time intervals in a day
        self.weekInterval = self.dayInterval * len(self.schTime.days)  # total time intervals of a week
        self.dayTime = {self.schTime.days[i]: i * self.dayInterval for i in range(len(self.schTime.days))}  # to help place events in the right time in the right day.
        self.schedule = {str(rms.name): [0 for _ in range(self.weekInterval)] for rms in self.locations}
        self.locationPreferences = {}
        self.metrics = []
        self.__unscheduledLocationCount = 0
        self.__arrangedLocationCount = 0
        self.__arrangedLocations = []

    #########################################################################

    # updates the schedule matrix by placing a event object in the allocated time
    def placeAEvent(self, event, location, forcePlace = False):
        if toDateTime(event.time.beginTime) < toDateTime(self.schTime.beginTime) or toDateTime(event.time.endTime) > toDateTime(self.schTime.endTime):          # check if the time falls within a day
            print(f"The time {event.time.beginTime, event.time.endTime} exceeds the specified schedule time!")
            return False
        timeIndices = self.__convertToScheduleTime(event.time)
        event.updateIndices(timeIndices)  # if there are indices present for that event, it is already placed
        if not forcePlace:                  # will not run these conditions if you are trying to force place a event in a location
            if event.seats > location.capacity:  # check if there are enough seats in the location
                #print(f"{event.name} exceeds location capacity at {location.name}")
                event.indices = []
                return False
            for start, end in timeIndices:
                if start != 0 and checkTimeGap(self.schedule[location.name], start, end, self.interval, self.timeGap):     # check if there are gaps before the event
                    #print(f"There needs to be a {self.timeGap} minute gap between {self.schedule[location.name][start - 1]} and {self.schedule[location.name][end]} at {location.name}")
                    event.indices = []
                    return False
                if self.schedule[location.name][start:end] != [0] * (end - start):  # check if there are any events in that time block
                    #print(f"{event.name} cannot be placed in the time slot {(event.time.beginTime, event.time.endTime)} as {location.name} is occupied!")
                    for sub_event in self.schedule[location.name][start:end]:
                        if sub_event != 0:
                            if not (toDate(sub_event.beginDate) > toDate(event.endDate)) or (toDate(sub_event.endDate) < toDate(event.beginDate)):
                                # If the event does NOT:
                                # a) begin after you end
                                # b) end before you begin
                                # reject the event
                                event.indices = []
                                return False
                
                
        # if all the conditions satisfy, then only place the indices
        for start, end in timeIndices:
            self.schedule[location.name][start:end] = [event] * (end - start)  # placing the event in the schedule
            event.placedLocation = location.name
        return True

    #########################################################################

    # private method which converts real time to a list of indices to be placed in the schedule
    def __convertToScheduleTime(self, time):
        return [(getIndex(str(subtractTime(self.schTime.beginTime, time.beginTime) / self.interval)) + self.dayTime[day],
                 getIndex(str(subtractTime(self.schTime.beginTime, time.endTime) / self.interval)) + self.dayTime[day]) for day in
                time.days if day in self.dayTime]

    #########################################################################

    # generates a plot of all the events that are currently in the schedule
    def visualizeSchedule(self, location="All", show="Code"):
        df = []
        tempdf = pd.DataFrame([dict(Location=x.name) for x in self.locations]).sort_values("Location")
        tempdf.reset_index(drop=True, inplace=True)
        displayLocations = self.locations
        if location != "All":
            displayLocations = [x for x in self.locations if x.name == location]
        for eachLocation in displayLocations:
            df += self.__getLocationAndEventInfo(eachLocation)
        df = pd.DataFrame(df)
        df['delta'] = df['Finish'] - df['Start']
        df = df.sort_values('Location')
        df.reset_index(drop=True, inplace=True)
        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Location", color=show, hover_name="Event", hover_data=             # initializing the figure
            {'Start': False, 'Finish': False, 'Time': True, 'Location': True, 'Dept': False, 'Event': False, 'Code': True}, template="plotly_dark")
        fig.update_yaxes(autorange="reversed")  # starts the first location at the top of Y-axis rather than at y=0
        dayLines = [i for i in range(self.dayInterval, self.weekInterval+1, self.dayInterval)]  # indices which denote a new day
        for i in range(len(dayLines)):
            fig.add_vline(x=dayLines[i], annotation_text=self.schTime.days[i], annotation_position="top left")  # adding a vertical line in those indices
        fig.update_layout(xaxis=dict(tickmode='array', tickvals=[x for x in range(0, self.weekInterval, int(60 / self.interval))],
                       ticktext=getTimeRange(self)))        # sets the time in the x-axis
        fig.update_layout(title="Event Arrangement", height=1000)
        fig.layout.xaxis.type = 'linear'
        for i in range(len(fig.data)):                              # This is to display the boxes of events in the figure
            fig.data[i].x = df[df[show] == df[show].unique()[i]]["delta"].tolist()
        return fig

    #########################################################################

    # private method that gets you all the info as a list of dictionaries of location and event startings and endings to be visualized
    def __getLocationAndEventInfo(self, location):
        uniqueEvents = list(set(self.schedule[location.name]))
        df = []
        for eachEvent in uniqueEvents:
            if eachEvent != 0:
                for start, end in eachEvent.indices:
                    df.append(dict(Location=eachEvent.placedLocation, Start=start, Finish=end, Event=eachEvent.name,
                                   Time=eachEvent.time.totalTime, Dept=eachEvent.dept, Code=eachEvent.eventCode))
        return df

    #########################################################################

    # returns a matrix of distances between buildings
    def getDistanceMatrix(self):
        locations = set(r.name.split(" ")[0] for r in self.locations)
        matrix = DistanceMatrix(len(locations))
        for i in range(matrix.size):
            for j in range(matrix.size):
                if i != j:
                    matrix.setItem(i, j, 1)
        return matrix.matrix

    #########################################################################

    # returns a list of dictionaries where event names are keys and the list of building preferences are values
    def getLocationPreferences(self):
        return self.locationPreferences

    #########################################################################

    # updates the dictionary with location preferences provided by a json file.
    def updateLocationPreferences(self, jsonFile):
        with open(jsonFile) as json_file:
            self.locationPreferences = json.load(json_file)

    #########################################################################

    # schedules events into locations in different phases
    def createSchedule(self, events, seed=0):
        random.seed(seed)
        eventCount = 0
        failures = 0
        totalLoops = 0
        waitingList = []
        finalList = []
        unscheduled = []
        random.shuffle(events)
        for eachEvent in events:              # 1st phase: place events in their past location
            totalLoops += 1
            pastLocation = eachEvent.getHistoricalLocations()
            if self.__checkAndPlaceARevents(eachEvent):           # if it is arranged, then place it in the right location and move on to next loop
                eventCount += 1
                continue
            if eachEvent.bldgCode == "nan":  # check if the event has a past location or not
                finalList.append(eachEvent)  # add them to a list to be added to schedule later
                continue
            if eachEvent.roomNumber == "nan":  # check if historical location has a location number or not
                waitingList.append(eachEvent)  # add them to a list to be added to schedule later
                continue
            locationSearch = searchForLocation(self.locations, pastLocation[0])
            if locationSearch is not None:
                if self.placeAEvent(eachEvent, searchForLocation(self.locations, pastLocation[0])):     # if location search returns a room, then only try to place event
                    eventCount += 1
                else:
                    failures += 1
                    waitingList.append(eachEvent)       # else add to waiting list, so that another phase can add it.
            else:
                failures += 1
                waitingList.append(eachEvent)

        random.seed(seed)
        random.shuffle(waitingList)
        for eachEvent in waitingList:          # 2nd phase: place events in their past location's building
            potentialLocation = getLocationsOfBuilding(self.locations, eachEvent.bldgCode)
            if not potentialLocation:
                finalList.append(eachEvent)
                continue
            for location in potentialLocation:
                totalLoops += 1
                if self.placeAEvent(eachEvent, location):
                    eventCount += 1
                    finalList = [x for x in finalList if x != eachEvent]
                    break
                else:
                    failures += 1
                    if eachEvent not in finalList: finalList.append(eachEvent)

        # finalList = list(set(finalList))
        finalList.sort(key=lambda x: x.name)

        random.seed(seed)
        random.shuffle(finalList)
        for eachEvent in finalList:        # 3rd phase: place events in other buildings
            if eachEvent.dept in self.getLocationPreferences():
                pLocations = self.getLocationPreferences()[eachEvent.dept]
            else:
                pLocations = []
            potentialLocation = []
            for bldg in pLocations:
                potentialLocation += getLocationsOfBuilding(self.locations, bldg)
            temp_rooms= list(set(self.locations).difference(set(potentialLocation)).difference(set(self.__arrangedLocations)))
            temp_rooms.sort(key=lambda x: x.name)
            potentialLocation += temp_rooms
            for location in potentialLocation:
                totalLoops += 1
                if self.placeAEvent(eachEvent, location):
                    eventCount += 1
                    unscheduled = [x for x in unscheduled if x != eachEvent]
                    break
                else:
                    failures += 1
                    if eachEvent not in unscheduled: unscheduled.append(eachEvent)

        while len(unscheduled) != 0:        #last phase place them in unscheduled locations
            unscheduled = self.__placeUnscheduledEvents(list(unscheduled))

        print(f"Events placed: {eventCount}/{len(events)}")
        print(f"Total failures: {failures}")
        print(f"Total loops: {totalLoops}")
        self.__getScheduleMetrics(events)

    #########################################################################

    # creates the past schedule i.e. a schedule with events that have historical location in them
    def createHistoricSchedule(self, events):
        eventCount = 0
        failures = 0
        waitingList = []
        for eachEvent in events:
            pastLocation = eachEvent.getHistoricalLocations()
            if not pastLocation:                                # check if the event has a past location or not
                waitingList.append(eachEvent)              # add them to a list to be added to schedule later
                continue
            if pastLocation[0].split(" ")[1] == "nan":          # check if historical location has a location number or not
                waitingList.append(eachEvent)              # add them to a list to be added to schedule later
                continue
            if self.placeAEvent(eachEvent, searchForLocation(self.locations, pastLocation[0]), forcePlace=True):
                eventCount += 1
                print(f"Placed events: {eventCount}/{len(events)}")
            else:
                failures += 1
        for eachEvent in waitingList:
            pastLocation = getLocationsOfBuilding(self.locations, eachEvent.getHistoricalLocations()[0].split(" ")[0])      # try to place rooms in the same building
            for location in pastLocation:
                if self.placeAEvent(eachEvent, location, forcePlace=True):
                    eventCount += 1
                    print(f"Placed events: {eventCount}/{len(events)}")
                    break
                else:
                    failures += 1

        print("Failures: ", failures)
        self.__getScheduleMetrics(events)
        print(self.metrics)

    #########################################################################

    # gives a score of how the schedule
    def score(self):
        score = 0
        for locationName, events in self.schedule.items():
            for crs in set(events):
                if crs != 0:
                    pastLocation = crs.getHistoricalLocations()[0]
                    if crs.placedLocation != pastLocation:       # if the location assigned is not the same as the historical location
                        if not pastLocation.startswith("AR"):    # if event pref was AR then it always gets placed in AR, although the number is different
                            if pastLocation.split(" ")[-1] != 'nan':  # if the csv mentioned building but not the location number for pastLocation
                                score -= 1
                                print(f"{crs.name} is placed at {crs.placedLocation} instead of {pastLocation}")
                            if getDept(crs.placedLocation) != getDept(pastLocation):
                                score -= 2
                                print(f"{crs.name} is placed at {crs.placedLocation} instead of {pastLocation}")
        return score

    #########################################################################

    # exports the schedule to a csv file
    def exportToCSV(self, allEvents):
        df = []
        for eachEvent in allEvents:
            df.append(dict(Code=eachEvent.eventCode, Event=eachEvent.name, Days=eachEvent.time.days,
                           Time=eachEvent.time.totalTime, Event_Enrollment = eachEvent.seats, Event_Capacity=eachEvent.capacity,
                           Event_Max_Enrollment=eachEvent.maxCapacity,  PastLocation= eachEvent.getHistoricalLocations(), Location=eachEvent.placedLocation, Metric = eachEvent.metric))
        df = pd.DataFrame(df)
        df.sort_values(df.columns[0],inplace=True)
        return df.to_csv

    #########################################################################

    # gives the metrics of the schedule
    def __getScheduleMetrics(self, allEvents):
        desiredLocation = 0
        sameBuilding = 0
        adjBuilding = 0
        wrongBuilding = 0
        for event in allEvents:
            if event.bldgCode == 'nan':      # if there is no desiredLocation then we are free to put it anywhere
                desiredLocation += 1
                event.metric = 1
            elif event.bldgCode == event.placedLocation.split(' ')[0] and event.roomNumber == event.placedLocation.split(' ')[1]:   # if same building and room then increment desiredLocation
                desiredLocation += 1
                event.metric = 1
            elif event.bldgCode == event.placedLocation.split(' ')[0] and event.roomNumber == 'nan':      # if same building but no room specified, then also increment desiredLocation
                desiredLocation += 1
                event.metric = 1
            elif event.bldgCode == event.placedLocation.split(' ')[0] and event.roomNumber != event.placedLocation.split(' ')[1]:   # if same building but different room then increment sameBuilding
                sameBuilding += 1
                event.metric = 2
            elif event.dept in self.getLocationPreferences():
                if event.placedLocation.split(' ')[0] in self.getLocationPreferences()[event.dept]:       # if placed building is in location preferences then increment adjBuilding
                    adjBuilding += 1
                    event.metric =3
                else:
                    wrongBuilding += 1
                    event.metric = 4
            else:
                wrongBuilding += 1
                event.metric = 4
        self.metrics = [desiredLocation, sameBuilding, adjBuilding, wrongBuilding]



    # adds unscheduled locations in the schedule
    def __addUnscheduledLocations(self):
        newLocation = 'UN ' + str(self.__unscheduledLocationCount)
        self.locations.append(Location(newLocation, 500, "Desks/Tables/Chairs/TV/Podium/White Board Projector"))
        self.schedule[newLocation] = [0 for _ in range(self.weekInterval)]
        self.__unscheduledLocationCount += 1

    #########################################################################

    # adds arranged (AR) locations in the schedule
    def __addArrangedLocations(self):
        newLocation = 'AR ' + str(self.__arrangedLocationCount)
        location = Location(newLocation, 500, "")
        self.locations.append(location)
        self.schedule[newLocation] = [0 for _ in range(self.weekInterval)]
        self.__arrangedLocationCount += 1
        self.__arrangedLocations.append(location)

    #########################################################################

    # adds unscheduled classes in unscheduled locations, and if adds new unscheduled locations if it is filled
    def __placeUnscheduledEvents(self, events):
        self.__addUnscheduledLocations()
        for event in events:
            if self.placeAEvent(event, self.locations[-1]):
                events.remove(event)
                print(f"{event.name} placed at {self.locations[-1].name}")
        return events

    #########################################################################

    # checks if a event is arranged or not and places it in AR locations
    def __checkAndPlaceARevents(self, event):
        pastLocation = event.getHistoricalLocations()[0]
        if pastLocation.split(" ")[0] == "AR":
            if self.placeAEvent(event, searchForLocation(self.locations, pastLocation)):
                return True
            for location in self.__arrangedLocations:
                if self.placeAEvent(event, location):
                    return True
            self.__addArrangedLocations()
            if self.placeAEvent(event, self.locations[-1]):
                return True
        return False

    #########################################################################

    # returns the schedule in the form of a 2D array(list)
    def printSchedule(self):
        return self.schedule

    #########################################################################



############################################################
################# CONSTRAINTERROR class ####################
############################################################
# User-defined error that gets raised if the constraint is not followed
class ConstraintError(Exception):
    def __init__(self, msg):
        self.msg = msg


############################################################
################ DISTANCEMATRIX class ######################
############################################################

# Returns a matrix that is symmetrical. i.e If (ai, aj) = 4 then (aj, ai) is also equal to 4
class DistanceMatrix:
    def __init__(self, size):
        if size <= 0:
            raise ValueError('size has to be positive')
        self.size = size
        self.matrix = np.zeros((size, size), dtype=np.int64)

    def setItem(self, i, j, value):
        self.matrix[i, j] = value
        self.matrix[j, i] = value



# Returns a list of Event objects of all the events present in the file.
def getAllEvents(fileName, courseFlag=False):
    eventDataset = pd.read_csv(fileName)
    if ("crs_cde" in eventDataset.columns) or courseFlag:
        eventDataset = eventDataset.dropna(subset=['begin_tim', 'end_tim'])
        return [Event(data['crs_cde'], data['crs_title'], data['crs_enrollment'], data['crs_capacity'],    # creates a Event object of each event in the dataset and adds it to the list
            data['max_enrollment'], Time(getTime(data['begin_tim']), getTime(data['end_tim']),  # create a Time object
                 [data['monday_cde'], data['tuesday_cde'], data['wednesday_cde'], data['thursday_cde'], data['friday_cde']]), str(data['bldg_cde']) + " " + str(data['room_cde']),
                   data['begin_dte'], data['end_dte']) for index, data in eventDataset.iterrows()]
    else:
        eventDataset = eventDataset.dropna(subset=['begin_time', 'end_time'])  # dropping the events which do not have allocated times since they are internships, independent studies etc
        return [Event(data['event_cde'], data['event_title'], data['event_enrollment'], data['event_capacity'],    # creates a Event object of each event in the dataset and adds it to the list
            data['max_enrollment'], Time(getTime(data['begin_time']), getTime(data['end_time']),  # create a Time object
                 [data['monday_cde'], data['tuesday_cde'], data['wednesday_cde'], data['thursday_cde'], data['friday_cde']]), str(data['bldg_cde']) + " " + str(data['room_cde']),
                   data['begin_date'], data['end_date']) for index, data in eventDataset.iterrows()]


# Returns a list of Location objects of all the locations present in the file
def getAllLocations(fileName):
    locationDataset = pd.read_csv(fileName)
    locationDataset = locationDataset.sort_values('Location')
    return [Location(rms['Location'], rms['Capacity'], splitAColumn(rms['Features'], "/"))
            for index, rms in locationDataset.iterrows()]
    # creates a Location object for each location present in the file; splitAColumn separates the furnishings in the location in a list for easier access

############################################################
#################### HELPER FUNCTIONS ######################
############################################################

# Splits a column with a specified delimiter
splitAColumn = lambda column, delimiter: str(column).split(delimiter)

# The file contains time in the format '././.... ..:..'; The helper function will remove the date and return the time
def getTime(time):
    search = re.findall("(\d?\d:\d\d):?", time)
    return search[0]

# converts time:string to a dateTime object and returns it
toDateTime = lambda time: datetime.timedelta(hours=int(time.split(":")[0]), minutes=int(time.split(":")[1]))

# Converts pure date strings of the form YYYY-MM-DD to dateTime objects
toDate = lambda date: datetime.date(year=int(date.split('-')[0]), month=int(date.split('-')[1]), day=int(date.split('-')[2]))

# Takes in two times as strings in the format ..:.. and returns the difference as a datetime object
def subtractTime(start, end):
    t1 = toDateTime(start)
    t2 = toDateTime(end)
    return t2 - t1

# checks if there are any events near an indices for the time gap that the user inputted
def checkTimeGap(locationIndices, start, end, timeInterval, timeGap):
    decrements = start - 1
    increments = end
    interval = timeInterval
    while interval <= timeGap:
        if isinstance(locationIndices[decrements], Event) or (isinstance(locationIndices[increments], Event)):
            return True
        interval += timeInterval
        decrements -= 1
        increments += 1
    return False



# takes in a time:String as a parameter and returns an index that can be put in the time list
def getIndex(time):
    temp = time.split(":")
    index = 60 * int(temp[0]) + int(temp[1])
    return index

# returns a list of times in string that represent the schedule week
def getTimeRange(schedule):
    timeRange = [str(x) + ":00" for x in range(int(schedule.schTime.beginTime.split(":")[0]), int(schedule.schTime.endTime.split(":")[0]))]
    #timeRange.append(schedule.schTime.endTime)
    return timeRange * len(schedule.schTime.days)

# receives event code (AAC 100 01) as returns the dept
def getDept(eventCode):
    dept = re.findall("[A-Z]+", eventCode)
    return dept[0] if dept != [] else ""

# searches for the specified locationName in the list of location objects and returns it
def searchForLocation(allLocations, locationName):
    if locationName.split(" ")[1] == "00" or locationName.split(" ")[1]=="000":
        locationName = locationName.split(" ")[0] + " " + "0"
    locationName = locationName.split(".")[0]
    for location in allLocations:
        if location.name == locationName:
            return location

# returns a list of locations of the building specified
def getLocationsOfBuilding(allLocations, bldg):
    return [location for location in allLocations if location.name.startswith(bldg)]

############################################################
###################### MAIN function #######################
############################################################
def main():
    allEvents = getAllEvents("templates/Event_Template.csv")
    allLocations = getAllLocations("templates/Location_Template.csv")
    schedule = Schedule(allLocations)
    schedule.updateLocationPreferences("templates/json_template.json")

    return schedule
