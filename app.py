from flask import Flask, render_template, url_for, redirect, request, send_file
#import jaydebeapi
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
#from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
#from wtforms.validators import InputRequired, Length
#from flask_sqlalchemy import SQLAlchemy
#from flask_bootstrap import Bootstrap
#from wtforms import StringField, PasswordField
#from flask_wtf import FlaskForm
#from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
#app.config['SECRET_KEY'] = 'wivTDJL107XUkGBLDRWaW0qJLWZnSRNl'
#app.config['SQLALCHEMY_DATABASE_URI'] ="postgresql://bonita:bonita@127.0.0.1:5432/bonita"

#database info

#maximum cases to display
max_count = 100

#database info
host = '127.0.0.1'
user = 'bonita'
password = 'bonita'

#conn = jaydebeapi.connect(
#        "org.h2.Driver",
#        "jdbc:h2:file:C:/bonitaServer/workspace/My project/h2_database/bonita_journal.db",
#        ["sa", ""],
#        "C:/bonitaServer/workspace/tomcat/server/lib/bonita/h2-1.4.199.jar")


#login_manager = LoginManager()
#login_manager.init_app(app)
#bootstrap = Bootstrap(app)
#db = SQLAlchemy(app)
#login_manager.login_view = 'login'

#class Utilisateurs(UserMixin, db.Model):
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(15), unique=True)
#    password = db.Column(db.String(500))

#@login_manager.user_loader
#def load_user(user_id):
#    return Utilisateurs.query.get(int(user_id))

#class LoginForm(FlaskForm):
#    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
#    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=500)])

#connects to what base you want from its name
def conn(base):
   conn = psycopg2.connect(host = host,
                        database = base,
                        user = user,
                        password = password)
   cursor = conn.cursor()
   return cursor

@app.route('/downloadTrail')
def download():
   return send_file('audit_trail.csv', as_attachment=True)

@app.route('/auditTrailGenerator', methods = ['GET', 'POST'])
def auditTrailGenerator():
   processList = getProcessDefList()
   filter = ""
   columns = ["Date and time event", "User name", "Process name", "Process version", "step name", "Entered values"]
   cursor = conn('audit_trail')
   if request.method == 'POST':
      dates = datePickerTreatment()
      addDateCondition = " AND date > %s AND date < %s"%(dates[0], dates[1])
      filter = filter + addDateCondition
      process = request.form.get("processes")
      if process !='All':
         for i in range (0, len(processList)):
             if process == processList[i][0]:
                add = "AND processname LIKE '%s'" %(processList[i][0])
                filter = add + filter
                processName = processList[i][0]
                processDispName = processList[i][1]
   rq = "SELECT date, bonitauser, processname, version, step, addeddata FROM operation WHERE 1=1 %s;"%(filter)
   cursor.execute(rq)
   trailData = cursor.fetchall()
   print("rq = ", rq)
   print("trailData = ",trailData)
   with open('audit_trail.csv', 'w') as trail:
      for i in range (0, len(columns)):
         trail.write(columns[i] + ",")
      trail.write("\n")
      for line in trailData:
         line = list(line)
         line[0] = datetime.fromtimestamp(line[0]/1000).strftime("%d-%m-%Y %H:%M:%S")
         for i in range (0, len(line)):
            line[i] = line[i].replace(": null", ": N/A")
            line[i] = line[i].replace(",",".")
            line[i] = line[i].replace(": true", ": ticked")
            print('writing = ', str(line[i])+",")
            trail.write(str(line[i]) + ",")
         trail.write('\n')
   return render_template('auditTrail.html', processList=processList)

@app.route('/<int:command_id>')
#@login_required
def command(command_id):
    list =  prepListToDisplayDetail(command_id)
    cursor = conn('bonita')
    cursor.execute("SELECT processdefinitionid FROM process_instance WHERE id = %s ;" %(command_id))
    defId = cursor.fetchone()[0]
    cursor.execute("SELECT displayname FROM process_definition WHERE processid = %s;"%(defId))
    name = cursor.fetchone()[0]
    return render_template('commandDetail.html', list=list, name = name )

@app.route('/statistics', methods=['GET', 'POST'])
def dispStats():
   valuesToDisp = []
   processList = getProcessDefList()
   totalDuration = 0
   filter = ""
   processName = ""
   processDispName = ""
   avgDuration = 0
#get filters, to add filters write this inside "if request.method=='POST':",
#   filter = request.form.get('[name of filter]')
#   if filter == [value]:
#      filteAdd = [things to concatenate to the query]
#      filter = filter + filterAdd
   if request.method == 'POST':
      dates = datePickerTreatment()
      addDateCondition = " AND startdate > %s AND startdate < %s"%(dates[0], dates[1])
      filter = filter + addDateCondition
      process = request.form.get("processes")
      if process != 'All':
          for i in range (0, len(processList)):
             if process == processList[i][0]:
                add = "AND name LIKE '%s'" %(processList[i][0])
                filter = add + filter
                processName = processList[i][0]
                processDispName = processList[i][1]
#make average process time
   avgDuration = autoDisplayProcessDuration(processName, filter)
#get archived process instances from which we do statistics
   cursor = conn('bonita')
   queryProcess = "SELECT sourceobjectid FROM arch_process_instance WHERE stateid=6 %s;" %(filter)
   print("query for name = ", queryProcess)
   cursor.execute(queryProcess)
   allArchProcessId = cursor.fetchall()
#get what statistics have to be displayed
   cursor = conn('settings')
   getWhatToDisplayRq = "SELECT processdefname,todisplay,label,basename,tablename,type,startdate,enddate,enddatetablename,enddatebasename,chaintosearch,disporder FROM dispstats WHERE processdefname = '%s' ORDER BY disporder;" %(processName)
   print("getWhatToDisplayRq = ",getWhatToDisplayRq)
   cursor.execute(getWhatToDisplayRq)
   listToDisp = cursor.fetchall()
   valuesToDisp = prepListToDisplayStats(listToDisp, allArchProcessId)
#message process filter needed
   if valuesToDisp == [] or valuesToDisp == None:
       valuesToDisp = [("Select a process to see its statistics",)]
   return render_template('statistics.html', valuesToDisp = valuesToDisp, processList = processList, processDispName = processDispName, avgDuration = avgDuration)

#returns the average duration of a process from its name
def autoDisplayProcessDuration(processName, filter):
   if processName == "":
      return 0
   cursor = conn('bonita')
   sum = 0
   processDurationRq = "SELECT startdate,enddate FROM arch_process_instance WHERE stateid = 6 AND name = '%s' %s;" %(processName, filter)
   print("processDurationRq = ", processDurationRq)
   cursor.execute(processDurationRq)
   durations = cursor.fetchall()
   if len(durations) == 0:
      return 0
   print('durations = ', durations)
   for duration in durations:
      sum = sum + (duration[1] - duration[0])//1000
   avg = timestampToDuration(sum/len(durations))
   return avg

#prepares the displays list from listWhatToDisplay (list of parameters from the disp table) and processIdsToStatFrom (list of id of archived instances)
def prepListToDisplayStats(listWhatToDisplay, processIdsToStatFrom):
   listValuesToDisplay = []
   startDates = []
   endDates = []
   toBePopedStart = []
   toBePopedEnd = []
   print("listWhatToDisplay = ",listWhatToDisplay)
   for toDisp in listWhatToDisplay:
      if toDisp[5]=='':
         listValuesToDisplay.append(("",toDisp[2]))
#if requested value is a duration
      if toDisp[5]=='duration':
#getting start dates where they have processIdsToStatFrom
         if toDisp[3]=='bonita':
            idColumn = 'sourceobjectid'
         else:
            idColumn = 'processinstanceid'
         sum = 0
         cursor = conn(toDisp[3])
         for id in processIdsToStatFrom:
            filterArchRq = "SELECT %s FROM %s WHERE %s = %s;" %(toDisp[6], toDisp[4], idColumn, id[0])
            print('filterArchRq = ', filterArchRq)
            cursor.execute(filterArchRq)
            res = cursor.fetchall()
            startDates.append(res[0])
         print('startdates = ', startDates)
#getting end dates and filtering them with processIdsToStatFrom
         if toDisp[9]=='bonita':
            idColumn = 'sourceobjectid'
         else:
            idColumn = 'processinstanceid'
         cursor = conn(toDisp[9])
         for id in processIdsToStatFrom:
            filterArchRq = "SELECT %s FROM %s WHERE %s = %s;" %(toDisp[7] ,toDisp[8], idColumn, id[0])
            print('filterArchRq = ', filterArchRq)
            cursor.execute(filterArchRq)
            res = cursor.fetchall()
            endDates.append(res[0])
         print('endDates = ', endDates)
#removing unfinished tasks from date lists
         length = len(endDates)
         for i in range (0, length):
            if endDates[i] == 0 or endDates[i] == None:
               toBePopedStart.append(startDates[i])
               toBePopedEnd.append(endDates[i])
         print('toBePopedStart = ', toBePopedStart)
         print('toBePopedEnd = ', toBePopedEnd)
         for pop in toBePopedStart:
            print('popstart = ',pop)
            startDates.remove(pop)
         for pop in toBePopedEnd:
            print('popend = ',pop)
            endDates.remove(pop)
#making the average
         for i in range (0, len(endDates)):
            print('endDates[0] = ',endDates[i])
            sum = sum + (endDates[i][0] - startDates[i][0])
         if len(endDates) == 0:
            avg = 0
         else:
            avg = sum/len(endDates)
         print('avg = ', avg)
         print('afterpop ends = ', endDates)
         print('afterpop starts = ',startDates)
         listValuesToDisplay.append((timestampToDuration(avg//1000), toDisp[2]))
#DISPLAY NUMBER OF PROCESS DURING PERIOD OF TIME
      elif toDisp[5]=='number':
         listValuesToDisplay.append((len(processIdsToStatFrom),toDisp[2]))
# TO HERE
   print("listValuesToDisplay = ",listValuesToDisplay)
   return listValuesToDisplay

@app.route('/arch<int:process_id>')
def archProcessDetail(process_id):
   list = prepListToDisplayDetailArch(process_id)
   cursor = conn('bonita')
   cursor.execute("SELECT processdefinitionid FROM arch_process_instance WHERE sourceobjectid = %s;" %(process_id))
   defId = cursor.fetchone()[0]
   cursor.execute("SELECT displayname FROM process_definition WHERE processid = %s;"%(defId))
   name = cursor.fetchone()[0]
   return render_template('archProcessDetail.html', list=list, name = name)

@app.route('/archivedOverview', methods=['GET', 'POST'])
def archivedIndex():
    archived = True
    filter = ""
    cursor = conn('bonita')
    processList = getProcessDefList()
    processNameFilter = ""
    disp = True
#get value of filter from user request
    if request.method == 'POST':
       dates = datePickerTreatment()
       addDateCondition = " AND startdate > %s AND startdate < %s"%(dates[0], dates[1])
       filter = filter + addDateCondition
       sort = request.form.get("sort")
       process = request.form.get("processes")
       if sort == "date_sort_desc":
          filter = filter + "ORDER BY startdate DESC"
       elif sort == "date_sort_asc":
          filter = filter + "ORDER BY startdate ASC"
       if process == 'All':
          print('all')
       else:
#modify SQL request according to the filter
          for i in range (0, len(processList)):
             if process == processList[i][0]:
                add = "AND name LIKE '%s'" %(processList[i][0])
                filter = add + filter
                processNameFilter = processList[i][1]
                print(process)
       queryTest = "SELECT COUNT(*) FROM arch_process_instance WHERE stateid=6 %s;"%(filter)
       cursor.execute(queryTest)
       count = cursor.fetchone()
       print('count =', count)
       if count[0] > max_count:
          disp = False
       queryProcess = "SELECT sourceobjectid,startdate,enddate,name,startedby FROM arch_process_instance WHERE stateid=6 %s LIMIT %s;" %(filter, max_count)
       cursor.execute(queryProcess)
       allProcess = cursor.fetchall()
       allProcess = prepProcessList(allProcess, archived)
       for process in allProcess:
          process = process + (timestampToDuration(process[2] - process[1]),)
       print('allProcess = ',allProcess)
       if sort == 'process_duration_sort_asc':
          allProcess.sort(key = lambda allProcess: allProcess[2]-allProcess[1])
       elif sort == 'process_duration_sort_desc':
          allProcess.sort(key = lambda allProcess: allProcess[2]-allProcess[1], reverse = True)
       print('allProcess = ',allProcess)
#get only the instances corresponding to the user request
    else:
       queryTest = "SELECT COUNT(*) FROM arch_process_instance WHERE stateid=6 %s;"%(filter)
       cursor.execute(queryTest)
       count = cursor.fetchone()
       print('count =', count)
       if count[0] > max_count:
          disp = False
       queryProcess = "SELECT sourceobjectid,startdate,enddate,name,startedby FROM arch_process_instance WHERE stateid=6 %s LIMIT %s;" %(filter, max_count)
       cursor.execute(queryProcess)
       allProcess = cursor.fetchall()
       allProcess = prepProcessList(allProcess, archived)
       print('allProcess = ',allProcess)
       for process in allProcess:
          process = process + (timestampToDuration(process[2] - process[1]),)
    print("disp =",disp)
    return render_template('archivedIndex.html',max_count = max_count, disp=disp, allProcess=allProcess, processList=processList, processNameFilter=processNameFilter)

@app.route('/overview', methods=['GET', 'POST'])
#@login_required
def index():
    archived = False
    cursor = conn('bonita')
    filter = "WHERE 1 = 1"
    processList = getProcessDefList()
    processNameFilter = ""
    addDateSort = ""
    disp = True
    if request.method == "POST":
       dates = datePickerTreatment()
       addDateCondition = " AND startdate > %s AND startdate < %s"%(dates[0], dates[1])
       filter = filter + addDateCondition
       sort = request.form.get("sort")
       process = request.form.get("processes")
#date filter
       if sort == "date_sort_asc":
          addDateSort =  " ORDER BY startdate DESC"
       elif sort == "date_sort_desc":
          addDateSort =  " ORDER BY startdate ASC"
#process filter
       if process == 'All':
          print ('all')
       else:
          for i in range (0, len(processList)):
             if process == processList[i][0]:
                add = " AND name LIKE '%s'" %(processList[i][0])
                filter = filter + add
                processNameFilter = processList[i][1]
#load the page with the filters
       filter = filter + addDateSort
       queryTest = "SELECT COUNT(*) FROM process_instance %s;"%(filter)
       cursor.execute(queryTest)
       count = cursor.fetchone()
       print('count =', count)
       if count[0] > max_count:
          disp = False
          allProcess = []
       else:
          queryProcess = "SELECT id,startdate,enddate,name,startedby FROM process_instance %s;" %(filter)
          cursor.execute(queryProcess)
          print('queryProcess = ', queryProcess)
          allCommand = cursor.fetchall()
          allCommand = prepProcessList(allCommand, archived)
          print('allCommand = ',allCommand)
          if sort == 'last_update_sort_asc':
             allCommand.sort(key = lambda allCommand: allCommand[9], reverse = True)
          elif sort == 'last_update_sort_desc':
             allCommand.sort(key = lambda allCommand: allCommand[9])
          print('allCommand = ',allCommand)
#first load of the page (no filters)
    else:
       queryTest = "SELECT COUNT(*) FROM process_instance %s;"%(filter)
       cursor.execute(queryTest)
       count = cursor.fetchone()
       print('count =', count)
       if count[0] > max_count:
          disp = False
       queryProcess = "SELECT id,startdate,enddate,name,startedby FROM process_instance %s LIMIT %s;" %(filter, max_count)
       cursor.execute(queryProcess)
       allCommand = cursor.fetchall()
       allCommand = prepProcessList(allCommand, archived)
    return render_template('index.html', disp=disp, a=allCommand, max_count=max_count, processList=processList, processNameFilter = processNameFilter)

#returns a tuple (timestamp of start date, timestamp of end date) these dates are collected through date pickers
def datePickerTreatment():
   endD = request.form.get("endD")
   startD = request.form.get("startD")
   print('startD =', startD)
   print('endD =', endD)
   if (endD == '' and startD == ''):
      endD = '2070-07-25'
      startD = '1970-07-25'
   elif (endD != '' and startD ==''):
      startD = '1970-07-25'
   elif (endD == '' and startD != ''):
      endD = '2070-07-25'
   endD = datetime.strptime(endD, '%Y-%m-%d')
   endD = int(datetime.timestamp(endD))
   startD = datetime.strptime(startD, '%Y-%m-%d')
   startD = int(datetime.timestamp(startD))
   return (startD*1000, endD*1000)

#returns a list of tuple (value to display, label of the value) from the id of the instance. It is to get the values to display in the details of the active instances overview
def prepListToDisplayDetail(id):
    cursor = conn('bonita')
#get infos of process
    processTypeRq = "SELECT processdefinitionid FROM process_instance WHERE id = %s;"%(id)
    cursor.execute(processTypeRq)
    print('processTypeRq = ',processTypeRq)
    defId = cursor.fetchone()[0]
    processVersionRq = "SELECT name,version FROM process_definition WHERE processid=%s"%(defId)
    cursor.execute(processVersionRq)
    processInfos = cursor.fetchall()
#get display instructions
    cursor = conn('settings')
    rq = "SELECT processdefname,todisplay,label,basename,tablename,type FROM dispdetail WHERE processdefname='%s' AND version=%s ORDER BY disporder;" %(processInfos[0][0], processInfos[0][1])
    print ('rq = ',rq)
    cursor.execute(rq)
    listToDisp = cursor.fetchall()
    print('listToDisp = ',listToDisp)
    list = []
#go and get everything from the instructions
    for i in range (0, len(listToDisp)):
       if (listToDisp[i][5] == 'label'):
          list.append(("",listToDisp[i][2]))
       else:
          if (listToDisp[i][3] == 'bonita'):
             field = 'id'
          elif (listToDisp[i][3] == 'bonitabusiness'):
             field = 'processInstanceId'
          cursor = conn(listToDisp[i][3])
          toDispRq = "SELECT %s FROM %s WHERE %s = %s;" %(listToDisp[i][1], listToDisp[i][4], field, id)
          cursor.execute(toDispRq)
          value = cursor.fetchone()[0]
          if value == None:
             value = 'N/A'
          elif listToDisp[i][5] == 'date':
             value = datetime.fromtimestamp(value/1000).strftime("%d-%m-%Y, %H:%M")
          list.append((value,listToDisp[i][2]))
          print('added: ', (value, listToDisp[i][2]))
    print ("list = ",list)
    return list

#same thing as above, except it is for archived instances, with different display instructions, to be displayed in the details of archived instances
def prepListToDisplayDetailArch(id):
#get infos of the process
    cursor = conn('bonita')
    processTypeRq = "SELECT processdefinitionid FROM arch_process_instance WHERE sourceobjectid = %s;"%(id)
    print(processTypeRq)
    cursor.execute(processTypeRq)
    defId = cursor.fetchone()[0]
    processInfosRq = "SELECT name,version FROM process_definition WHERE processid=%s;"%(defId)
    cursor.execute(processInfosRq)
    processInfos = cursor.fetchall()
#get display instructions
    cursor = conn('settings')
    rq = "SELECT processdefname,todisplay,label,basename,tablename,type FROM dispdetailarch WHERE processdefname='%s' AND version=%s ORDER BY disporder;" %(processInfos[0][0], processInfos[0][1])
    print ('rq = ',rq)
    cursor.execute(rq)
    listToDisp = cursor.fetchall()
    print('listToDisp = ',listToDisp)
    list = []
#get everything needed to build list
    for i in range (0, len(listToDisp)):
       print('listToDisp = ', listToDisp[i])
       if (listToDisp[i][5] == 'label'):
          list.append(("",listToDisp[i][2]))
       else:
          if (listToDisp[i][3] == 'bonita'):
             field = 'sourceobjectid'
          elif (listToDisp[i][3] == 'bonitabusiness'):
             field = 'processInstanceId'
          cursor = conn(listToDisp[i][3])
          toDispRq = "SELECT %s FROM %s WHERE %s = %s;" %(listToDisp[i][1], listToDisp[i][4], field, id)
          cursor.execute(toDispRq)
          value = cursor.fetchone()[0]
          if value == None:
             value = "N/A"
          elif listToDisp[i][5] == 'date':
             value = datetime.fromtimestamp(value/1000).strftime("%d-%m-%Y, %H:%M")
          list.append((value,listToDisp[i][2]))
          print('added: ', (value, listToDisp[i][2]))
    print ("list = ",list)
    return list

#returns a list of values to display in the overview
def prepProcessList(processList, archived):
#functions need to be in this order, meaning, StartUserOfProcess first, step second etc..
   processList = addStartUserOfProcess(processList)
   if (archived == False):
      processList = addStep(processList)
   processList = addDateFormat(processList, archived)
   if (archived):
      processList = addProcessDuration(processList)
      print('processList = ', processList)
   if (archived == False):
      for i in range (0,len(processList)):
         businessInfos = getBusinessInfo(processList[i][0], processList[i][3])
         processList[i] = processList[i] + businessInfos
         print("process = ",processList[i])
   cursor = conn('bonita')
   for i in range (0, len(processList)):
      cursor.execute("SELECT displayname FROM process_definition WHERE name = '%s';"%(processList[i][3]))
      dispName = cursor.fetchone()
      processList[i] = processList[i] + dispName
   print("processList = ",processList)
   return processList

def getBusinessInfo(id, processName):
   cursor = conn('bonitabusiness')
   tableName = "%sMeta"%(processName)
   rqMeta = "SELECT lastupdate, stepname, supposedtoact FROM %s WHERE processinstanceid = %s;"%(tableName, id)
   cursor.execute(rqMeta)
   businessInfos = cursor.fetchall()
   print('rqMeta = ',rqMeta)
   print('businessInfos',businessInfos)
   businessInfos[0] = businessInfos[0] + ( datetime.fromtimestamp(businessInfos[0][0]/1000).strftime("%d-%m-%Y, %H:%M"), )
   return businessInfos[0]

#returns a string ogiving the amount of months, days, hours, minutes, seconds from a timestamp
def timestampToDuration(seconds):
    minutes = seconds // 60
    secondsRest = seconds % 60
    secondsRest = int(secondsRest)
    hours = minutes // 60
    minutesRest = minutes % 60
    minutesRest = int(minutesRest)
    days = hours // 24
    hoursRest = hours % 24
    hoursRest = int(hoursRest)
    weeks = days // 7
    daysRest = days % 7
    daysRest = int(daysRest)
    months = weeks // 4
    months = int(months)
    processDuration = "%s months, %s days, %sh, %sm, %ss," %(months, daysRest, hoursRest, minutesRest, secondsRest)
    return processDuration

#adds to a list the corresponding duration of process, used only in prepProcessList
def addProcessDuration(processList):
   for i in range (0, len(processList)):
      seconds = (processList[i][2]//1000) - (processList[i][1]//1000)
      minutes = seconds // 60
      secondsRest = seconds % 60
      hours = minutes // 60
      minutesRest = minutes % 60
      days = hours // 24
      hoursRest = hours % 24
      weeks = days // 7
      daysRest = days % 7
      months = weeks // 4
      processDuration = "%s months, %s days, %sh, %sm, %ss," %(months, daysRest, hoursRest, minutesRest, secondsRest)
      processList[i] = processList[i] + (processDuration,)
   return processList

#same as above, except it adds dates of start, end or last update.
def addDateFormat(processList, archived):
   for i in range (0, len(processList)):
      processList[i] = processList[i] + (datetime.fromtimestamp(processList[i][1]/1000).strftime("%d-%m-%Y, %H:%M"),)
      if (archived):
         processList[i] = processList[i] + (datetime.fromtimestamp(processList[i][2]/1000).strftime("%d-%m-%Y, %H:%M"),)
   return processList

#adds step to list, same use as above
def addStep(processList):
   for i in range(0, len(processList)):
      step = getWhatInBusiness(processList[i][0], processList[i][3], "stepnumber")
      processList[i]= processList[i] + step
      print(processList[i])
   return processList

#same, it adds the first and last name of initiator
def addStartUserOfProcess(processList):
   for i in range (0, len(processList)):
      user = getUserFromId(processList[i][4])
      processList[i] = processList[i] + (user[0],)
      processList[i] = processList[i] + (user[1],)
      print(processList[i])
   return processList

#gets first name and last name from an user id
def getUserFromId(id):
   cursor=conn('bonita')
   rq = "SELECT firstname,lastname FROM user_ WHERE id=%s;" %(id)
   cursor.execute(rq)
   name = cursor.fetchone()
   return name

#gets what you want in bonitabusiness base
def getWhatInBusiness(id, data, columnName):
   cursor=conn('bonitabusiness')
   rq="SELECT %s FROM %s WHERE processInstanceId=%s;" %(columnName, data, id)
   print(rq)
   cursor.execute(rq)
   stepNb=cursor.fetchone()
   return stepNb

#@app.route('/login', methods=['GET', 'POST'])
#def login():
    #new_user = Utilisateurs(username='MLETELLIER', password='password')
    #db.session.add(new_user)
    #db.session.commit()
#    form = LoginForm()
#    if form.validate_on_submit():
#        user = Utilisateurs.query.filter_by(username=form.username.data).first()
#        if user:
#            if user.password==form.password.data:#check_password_hash(user.password, form.password.data):
#                login_user(user)
#                return redirect(url_for('index'))
        #return '<h1>' + form.username.data + ' ' + form.password.data + '</h1>'
#        return '<h1>Invalid username or password</h1>'
#    return render_template('login.html', form=form)

#@app.route('/logout')
#@login_required
#def logout():
#    logout_user()
#    return redirect(url_for('login'))

#gets id, name, displayname of all the process definition, used to display options in filter
def getProcessDefList():
    cursor = conn('bonita')
    cursor.execute("SELECT distinct(name),displayname FROM process_definition")
    processes = cursor.fetchall()
    return processes

if __name__ == '__main__':
    app.run(host = "0.0.0.0")

