from py2neo import Graph, Node, Relationship
import settings

import datetime
import timestring
from dateutil.parser import parse as parsedate

from flask import Flask, request, render_template, redirect, session, url_for

app = Flask(__name__)
app.debug = settings.DEBUG
app.config.from_object(settings)

graph = Graph(settings.GRAPHENEDB_URL)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/nodes/', methods=['POST', 'GET'])
@app.route('/nodes/<node_id>/', methods=['PUT', 'GET'])
def nodes(node_id=None):
    if node_id:
        def get():
            pass
        def put():
            pass
    else:
        def get():
            pass
        def post():
            pass
    
    return locals()[request.method.lower()]()

@app.route('/nodes/that/owe/<node_id>/', methods=['GET'])
def nodes(node_id):
    pass

@app.route('/nodes/owed/by/<node_id>/', methods=['GET'])
def nodes(node_id):
    pass

@app.route('/ious/', methods=['POST', 'GET'])
@app.route('/ious/<owes>/=>/<to>/', methods=['POST', 'GET'])
@app.route('/ious/<iou_id>/', methods=['PUT', 'GET'])
def ious(owes=None, to=None, iou_id=None):
    if owes and to:
        def get():
            pass
        def post():
            pass
    elif iou_id:
        def get():
            pass
        def put():
            pass
    else:
        def get():
            pass
        def post():
            pass

    return locals()[request.method.lower()]()

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(days=1000)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
