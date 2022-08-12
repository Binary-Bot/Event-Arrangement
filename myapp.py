# Import required library files
import dash, base64, pandas as pd, io, copy
import datetime, json, random, time
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from base64 import b64encode
from dash import dcc
from dash import html
from dash import dash_table

# Import the source code as module
import classroomArrangement as ca

print("Creating Default Schedule on app load")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = "Event Placer"
server = app.server

# to display the data table
def parseTemplate(filename):
    df = pd.read_csv(filename)
    return html.Div([
        dash_table.DataTable(
            df.to_dict('records'),
            [{'name': i, 'id': i} for i in df.columns],
            style_header={
                'backgroundColor': 'black',
                'color': 'white'
            },
            style_data={
                'backgroundColor': 'rgb(50, 50, 50)',
                'color': 'white'
            },
            style_table={'overflowX': 'auto'}
        ),
        html.Hr()  # horizontal line
    ])

#validates the csv file by checking all if all the required columns are present or not
def validateEventFile(file):
    try:
        data = pd.read_csv(file)
        if "crs_cde" in data.columns:
            event = (data['crs_cde'], data['crs_title'], data['crs_enrollment'], data['crs_capacity'],    # creates a Event object of each event in the dataset and adds it to the list
            data['max_enrollment'], data['begin_tim'],data['end_tim'],  # create a Time object
                 [data['monday_cde'], data['tuesday_cde'], data['wednesday_cde'], data['thursday_cde'], data['friday_cde']], str(data['bldg_cde']) + " " + str(data['room_cde']),
                   data['begin_dte'], data['end_dte'])
        else:
            event = (data['event_cde'], data['event_title'], data['event_enrollment'], data['event_capacity'],    # creates a Event object of each event in the dataset and adds it to the list
                 data['max_enrollment'], data['begin_time'], data['end_time'],  # create a Time object
                 [data['monday_cde'], data['tuesday_cde'], data['wednesday_cde'], data['thursday_cde'], data['friday_cde']], str(data['bldg_cde']) + " " + str(data['room_cde']),
                 data['begin_date'], data['end_date'])
    except KeyError:
        return False
    except:
        return False
    return True

#validates the csv file by checking all if all the required columns are present or not
def validateLocationFile(file):
    try:
        rms = pd.read_csv(file)
        location = (rms['Location'], rms['Capacity'], splitAColumn(rms['Features'], "/"))
    except KeyError:
        return False
    except:
        return False
    return True

# Splits a column with a specified delimiter
splitAColumn = lambda column, delimiter: str(column).split(delimiter)

#all the controls that can be altered by the user
controls = [
    dbc.Card([html.H3("Events", style={"font-family":'Arial'}),
              html.Div([dcc.Markdown("""
              Select a CSV file for the events.  This CSV file should contain the headers: `event_cde`, `event_title`, `event_enrollment`, `event_capacity`, `max_enrollment`,`begin_time`, `end_time`,  
              `begin_date`, `end_date`, `bldg_cde`, `room_cde`, `monday_cde`, `tuesday_cde`, `wednesday_cde`, `thursday_cde`, `friday_cde`, `saturday_cde`, `sunday_cde`
              - `event_cde`, `bldg_cde`: must start with a 2-3 long letters
              - `begin_time`, `end_time`: must be in the 24hr format xx:xx where x are digits
              - `begin_date`, `end_date`: must be in YYYY-MM-DD format
              - `...day_cde`: must start with the first letter of the day (e.g `monday_cde`: M) except: `thursday_cde`: R, `saturday_cde`: Sa, `sunday_cde`: Su
              """, style={"font-size": "12pt"}),
                html.Div([
                    dbc.Button("Download Event Template", id="event-download",color='primary', outline=True),
                    dcc.Download(id="eventDownload")
                ]),
              parseTemplate("templates/Event_Template.csv"),], style={'backgroundColor':"#222222"}),
              dcc.Upload(['Drag and Drop or ', html.A('Select a File')],
                          style={
                              "color": "darkgray",
                              "width": "100%",
                              "height": "50px",
                              "lineHeight": "50px",
                              "borderWidth": "1px",
                              "borderStyle": "dashed",
                              "borderRadius": "5px",
                              "borderColor": "darkgray",
                              "textAlign": "center",
                              "padding": "2rem 0",
                              "margin-bottom": "2rem",
                          },
                          id="courseFile"
                          ),
            html.Div(id='output-data1-upload')]
             , style={"box-shadow": "2px 2px 2px 2px lightgrey", 'padding':"20px", 'border-radius': '5px', 'position': 'relative', 'margin-bottom': "2rem"}),

              dbc.Card([html.H3("Locations"),
              html.Div([dcc.Markdown("""
              Select a CSV file for the locations.  This CSV file should contain the following headers: `Location`, `Capacity`, `Features`
              - `Location`: Should be in the format: bldg_cde<space>room_cde
              - `Features`: Should be in the format: smth/smth/smth
              """, style={"font-size": "12pt"}),
              html.Div([
                  dbc.Button("Download Location Template", id="location-download",color='primary', outline=True),
                  dcc.Download(id="locationDownload")
              ]),
              parseTemplate("templates/Location_Template.csv"),], style={'backgroundColor':"#222222"}),
              dcc.Upload(['Drag and Drop or ', html.A('Select a File')],
                          style={
                              "color": "darkgray",
                              "width": "100%",
                              "height": "50px",
                              "lineHeight": "50px",
                              "borderWidth": "1px",
                              "borderStyle": "dashed",
                              "borderRadius": "5px",
                              "borderColor": "darkgray",
                              "textAlign": "center",
                              "padding": "2rem 0",
                              "margin-bottom": "2rem",
                          },
                         id="roomFile"
                          ),
    html.Div(id='output-data2-upload'),
                   ], style={"box-shadow": "2px 2px 2px 2px lightgrey", 'padding':"20px", 'border-radius': '5px', 'position': 'relative', 'margin-bottom': "2rem"}),
    html.Div(id='space2'),
    dbc.Card([html.H3("Location Preferences (Optional)"),
              html.Div([dcc.Markdown("""
              Select a JSON file for the location preferences.  If not provided, events will be placed randomly in any location.  The JSON file should be in the following format:     
              {<event_cde>: [`bldg_cde`, `bldg_cde`, `bldg_cde`], 
               <event_cde>: [`bldg_cde`]...}
              """, style={"font-size": "12pt"}),
              html.Div([
                  dbc.Button("Download Json Template", id="json-download",color='primary', outline=True),
                  dcc.Download(id="jsonDownload")
              ]),# dcc.Store stores the intermediate value
    dcc.Store(id='intermediate-value')
              ], style={'backgroundColor':"#222222"}),
              dcc.Upload(['Drag and Drop or ', html.A('Select a File')],
                          style={
                              "color": "darkgray",
                              "width": "100%",
                              "height": "50px",
                              "lineHeight": "50px",
                              "borderWidth": "1px",
                              "borderStyle": "dashed",
                              "borderRadius": "5px",
                              "borderColor": "darkgray",
                              "textAlign": "center",
                              "padding": "2rem 0",
                              "margin-bottom": "2rem",
                          },
                         id="jsonFile"
                          ),
    html.Div(id='output-data3-upload'),
                   ], style={"box-shadow": "2px 2px 2px 2px lightgrey", 'padding':"15px", 'border-radius': '5px', 'position': 'relative', 'margin-bottom': "2rem"}),
    dbc.Card([dbc.Label("Days to be in Schedule:"),
              dbc.Checklist(
                    id = 'dayPicker',
                    options= [{"label": x, "value": x} for x in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']],
                    value=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'], label_checked_style={"color": "#6a9ede"},
                    input_checked_style={
                        "backgroundColor": "#6a9ede",
                        "borderColor": "#ea6258",
                    },
                    inline=True,
                    style={"textAlign": "center","justify-content": "center"}
               )], style={'padding':"15px", 'border-radius': '5px', 'position': 'relative'}),
    dbc.Card([dbc.Label("Time range of a day:"),
                   html.Div([dcc.RangeSlider(0, 24, 1, value=[6, 24], id='scheduleTimeSlider')]),
             ]),
    dbc.Card([dbc.Row([dbc.Col([dbc.Label("Time interval:"),
              dbc.Select(
                  id = 'timeInterval',
                  options = [{"label": x, "value": x} for x in range(0, 61, 10)],
                  value=10
            )]),
            dbc.Col([dbc.Label("Time Gap between courses:"),
              dbc.Select(
                  id='timeGap',
                  options=[{"label": x, "value": x} for x in range(0, 361, 10)],
                  value=10
                )])])
              ]),
    dbc.Card([dbc.Button(id='generateButton', color='primary', outline=True, n_clicks=0, children='Generate Schedule'),
             dcc.Markdown("""
                           Events will be placed at random with each click of the generate schedule button
                           """, style={"font-size": "8pt", 'text-align': "center"})
             ]),
    html.Div([
        dbc.Card(dbc.Button("Download Schedule as CSV", id="downloadBtn",color='primary', outline=True, n_clicks=0)),
        dcc.Download(id="download"),
        html.Div([dcc.Markdown("""
              In the CSV under metric column, 1: Events placed in desired location, 2: Events placed in same building, 
              3: Events placed in location preference, 4: Events placed in unpreferred location.
              """, style={"font-size": "8pt", 'text-align': 'center'})]),
    html.Div([
        dbc.Card(dbc.Button("Download Figure", id="downloadFig", color='primary', outline=True)),
        dcc.Download(id="dwnFig")
    ])], id = 'dwnButtons'),
    html.Div(id="displayMetric")
    ]

title = html.H1("EVENT PLACER", style={'margin-top': 5, 'text-align': 'center', 'font': "Candara", 'align': 'center'})
app.layout = dbc.Container([
    dbc.Row([dbc.Col(title, md=20)]),
    dcc.Store(id='seed'),
    dbc.Card(dbc.Row([c for c in controls]), body=True, style={"box-shadow": "2px 2px 2px lightgrey", 'padding':"15px", 'border-radius': '5px', 'position': 'relative'}),
    html.Div([dcc.Graph(id="scheduleGraph")], style={'padding':"15px", 'border-radius': '5px', 'position': 'relative'})
    
])

# to display the csv file name after it has been uploaded
def parse_contents(contents, filename, date):
    return html.Div([html.H6(filename), html.H6(datetime.datetime.fromtimestamp(date))])


# displays the csv filename beneath the upload div
@app.callback(Output('output-data1-upload', 'children'),
              Input('courseFile', 'contents'),
              State('courseFile', 'filename'),
              State('courseFile', 'last_modified'))
def update_output(content, name, date):
    if content is not None:
        content_type, content_string = content.split(',')
        course_decoded = base64.b64decode(content_string)
        if validateEventFile(io.StringIO(course_decoded.decode('utf-8'))):
            return html.Div([parse_contents(content, name, date),
                             html.Img(src="https://img.icons8.com/stickers/100/000000/checked.png", height="25",
                                      width="25")])
        return html.Div([parse_contents(content, name, date),
                         html.Img(src="https://img.icons8.com/flat-round/64/000000/delete-sign.png", height="25",
                                  width="25")])
    

# displays the csv filename beneath the upload div
@app.callback(Output('output-data2-upload', 'children'),
              Input('roomFile', 'contents'),
              State('roomFile', 'filename'),
              State('roomFile', 'last_modified'))
def update_output(content, name, date):
    if content is not None:
        content_type, content_string = content.split(',')
        course_decoded = base64.b64decode(content_string)
        if validateLocationFile(io.StringIO(course_decoded.decode('utf-8'))):
            return html.Div([parse_contents(content, name, date),
                             html.Img(src="https://img.icons8.com/stickers/100/000000/checked.png", height="25", width="25")])
        return html.Div([parse_contents(content, name, date),
                         html.Img(src="https://img.icons8.com/flat-round/64/000000/delete-sign.png", height="25", width="25")])


# displays the json filename beneath the upload div
@app.callback(Output('output-data3-upload', 'children'),
              Input('jsonFile', 'contents'),
              State('jsonFile', 'filename'),
              State('jsonFile', 'last_modified'))
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        return parse_contents(list_of_contents, list_of_names, list_of_dates)


# generates a schedule object for the app to use
def generateSchedule(dayPicker, scheduleTimeSlider, timeInterval, timeGap, courseFile, roomFile, jsonFile, seed):
    print("Current seed:",seed)
    if (courseFile is not None) and (roomFile is not None):
        content_type, content_string = courseFile.split(',')
        course_decoded = base64.b64decode(content_string)
        #print("Object hash:",hash(schedule))

        content_type, content_string = roomFile.split(',')
        room_decoded = base64.b64decode(content_string)
        
        if jsonFile is not None:
            content_type, content_string = jsonFile.split(',')
            json_decoded = base64.b64decode(content_string)
        else:
            json_decoded = False

        allEvents = ca.getAllEvents(io.StringIO(course_decoded.decode('utf-8')), True)
        allRooms = ca.getAllLocations(io.StringIO(room_decoded.decode('utf-8')))

        startTime = str(scheduleTimeSlider[0]) + ":00"
        endTime = str(scheduleTimeSlider[1]) + ":00"
        days = {"Sunday": "Su", "Monday": "M", "Tuesday": "T", "Wednesday":"W", "Thursday":"R", 'Friday':"F", "Saturday":"Sa"}
        pickedDays = [days[value] for value in dayPicker]

        schedule = ca.Schedule(allRooms, time=ca.Time(startTime, endTime, pickedDays), interval=int(timeInterval), timeGap=int(timeGap))
        if json_decoded:
            schedule.locationPreferences = json.loads(json_decoded.decode('utf-8'))

        schedule.createSchedule(allEvents, seed)
        print("Object hash:",hash(schedule))

        return schedule, allEvents
    else:
        print("Loading Default Schedule")
        allEvents =ca.getAllEvents("templates/Event_Template.csv")
        allRooms = ca.getAllLocations("templates/Location_Template.csv")
        schedule = ca.Schedule(allRooms)
        schedule.createSchedule(allEvents, seed)
        print("Object hash:",hash(schedule))
        return schedule, allEvents


@app.callback(
    Output("eventDownload", "data"),
    Input("event-download", "n_clicks"),
    prevent_initial_call=True,
)
def downloadEventTemplate(n_clicks):
    df = pd.read_csv("templates/Event_Template.csv")
    return dcc.send_data_frame(df.to_csv, "event_template.csv")


@app.callback(
    Output("locationDownload", "data"),
    Input("location-download", "n_clicks"),
    prevent_initial_call=True,
)
def downloadLocationTemplate(n_clicks):
    df = pd.read_csv("templates/Location_Template.csv")
    return dcc.send_data_frame(df.to_csv, "location_template.csv")


@app.callback(
    Output("jsonDownload", "data"),
    Input("json-download", "n_clicks"),
    prevent_initial_call=True,
)
def downloadJsonTemplate(n_clicks):
    df = pd.read_csv("templates/json_template.json")
    return dcc.send_data_frame(df.to_csv, "json_template.json")


def getMetricsDiv(schedule):
    metrics = schedule.metrics
    return dbc.Card([html.Div([
        html.H4("Schedule Created!!!"),
        dcc.Markdown(f"""
        - {metrics[0]/sum(metrics) :.1%} of the events were placed in the desired location.
        - {metrics[1]/sum(metrics) :.1%} of the events were placed in the the same building.
        - {metrics[2]/sum(metrics) :.1%} of the events were placed in the building entered in location preference.
        - {metrics[3]/sum(metrics) :.1%} of the events were placed in unpreferred locations. 
        """, style = {"font-size":'10pt'})])
    ])

# displays the graph in the app
@app.callback(
    Output("displayMetric", "children"),
    Output("scheduleGraph", "figure"),
    Output("seed", "data"),
    Input("generateButton", "n_clicks"),
    State("dayPicker", "value"),
    State("scheduleTimeSlider", "value"),
    State("timeInterval", "value"),
    State("timeGap", "value"),
    State('courseFile', 'contents'),
    State('roomFile', 'contents'),
    State('jsonFile', 'contents')
)
def generateGraph(nClicks, dayPicker, scheduleTimeSlider, timeInterval, timeGap, courseFile, roomFile, jsonFile):
    seed = round(time.time())
    schedule, allEvents= generateSchedule(dayPicker, scheduleTimeSlider, timeInterval, timeGap, courseFile, roomFile, jsonFile, seed)
    return getMetricsDiv(schedule), schedule.visualizeSchedule(), seed

@app.callback(
    Output("download", "data"),
    Input("downloadBtn", "n_clicks"),
    State("dayPicker", "value"),
    State("scheduleTimeSlider", "value"),
    State("timeInterval", "value"),
    State("timeGap", "value"),
    State('courseFile', 'contents'),
    State('roomFile', 'contents'),
    State('jsonFile', 'contents'),
    State('seed', 'data'),
    prevent_initial_call=True,
)
def downloadCSV(n_clicks, dayPicker, scheduleTimeSlider, timeInterval, timeGap, courseFile, roomFile, jsonFile, seed):
    schedule, allEvents = generateSchedule(dayPicker, scheduleTimeSlider, timeInterval, timeGap, courseFile, roomFile, jsonFile, seed)
    file = schedule.exportToCSV(allEvents)
    return dcc.send_data_frame(file, "classroom.csv")

@app.callback(
    Output("dwnFig", "data"),
    Input("downloadFig", "n_clicks"),
    State("dayPicker", "value"),
    State("scheduleTimeSlider", "value"),
    State("timeInterval", "value"),
    State("timeGap", "value"),
    State('courseFile', 'contents'),
    State('roomFile', 'contents'),
    State('jsonFile', 'contents'),
    State('seed', 'data'),
    prevent_initial_call=True,
)
def downloadGraph(n_clicks, dayPicker, scheduleTimeSlider, timeInterval, timeGap, courseFile, roomFile, jsonFile, seed):
    schedule, allEvents = generateSchedule(dayPicker, scheduleTimeSlider, timeInterval, timeGap, courseFile, roomFile, jsonFile, seed)
    fig = schedule.visualizeSchedule()
    filename = "schedule figure.html"
    fig.write_html(filename)
    return dict(content=fig.to_html(), filename=filename)

# Running the server
if __name__ == "__main__":
    app.run_server(host='0.0.0.0', port=8080, debug=True, use_reloader=False)
