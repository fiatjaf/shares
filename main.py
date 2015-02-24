import settings

import datetime
import timestring
import neo4j
from neo4j.manager import ConnectionManager
from dateutil.parser import parse as parsedate

from uuid import uuid4
uuid = lambda : str(uuid4())

from flask import Flask, request, render_template, redirect, session, jsonify

app = Flask(__name__)
app.debug = settings.DEBUG
app.config.from_object(settings)

graph = ConnectionManager(settings.GRAPHENEDB_URL)

### ASSUMPTIONS
# 'rate' is the YEARLY interest rate for each IOU.
# all values are given in cents -- so $1 is written as the integer 100
#
###

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/agents/<agent_handle>/', methods=['PUT', 'GET'])
@app.route('/agents/', methods=['POST', 'GET'])
def agents(agent_handle=None):
    if agent_handle:
        def get():
            r = graph.request('MATCH (a:Agent {handle: {H}}) RETURN a', H=agent_handle)
            return jsonify(r.rows[0].a)
        def put():
            pass
    else:
        def get():
            r = graph.request('MATCH (a:Agent) RETURN a')
            return jsonify({'agents': [row.a for row in r.rows]})
        def post():
            r = graph.request('''
                MERGE (a:Agent {handle: {H}})
                SET a.default_rate = {RATE}
                RETURN a
                ''',
                H=request.form['handle'],
                RATE=int(request.form.get('default_rate') or 0)
            )
            return redirect('/agents/' + r.rows[0].a['handle'])

    return locals()[request.method.lower()]()

@app.route('/agents/that/owe/<agent_handle>/', methods=['GET'])
def agents_that_owe(agent_handle):
    pass

@app.route('/agents/owed/by/<agent_handle>/', methods=['GET'])
def agents_owed_by(agent_handle):
    pass

@app.route('/ious/<owes>/=>/<to>/', methods=['POST', 'GET'])
@app.route('/ious/<iou_id>/', methods=['PUT', 'GET'])
@app.route('/ious/', methods=['POST', 'GET'])
def ious(owes=None, to=None, iou_id=None):
    if owes and to:
        def get():
            pass
        def post():
            pass
    elif iou_id:
        def get():
            r = graph.request('''
                MATCH (i)-[:ISSUED]->(iou:IOU {id: {ID}})-[:HELDBY]->(b)
                RETURN i, iou, b
            ''', ID=iou_id)
            iou = r.rows[0].iou
            iou['issuer'] = r.rows[0].i['handle']
            iou['bearer'] = r.rows[0].b['handle']
            return jsonify(iou)
        def put():
            pass
    else:
        def get():
            r = graph.request('''
                MATCH (i)-[:ISSUED]->(iou:IOU)-[:HELDBY]->(b)
                RETURN i, iou, b
            ''')
            ious = []
            for row in r.rows:
                iou = row.iou
                iou['issuer'] = row.i['handle']
                iou['bearer'] = row.b['handle']
                ious.append(iou)
            return jsonify({'ious': ious})
        def post():
            r = graph.request('''
                MATCH (i:Agent {handle:{ISSUER_HANDLE}})
                MATCH (b:Agent {handle:{BEARER_HANDLE}})
                OPTIONAL MATCH (b)-[line:Line]->(i)
                CREATE (iou:IOU {
                    id: {ID},
                    issued_at: {DATE},
                    value: {VAL},
                    rate: 
                      CASE
                        WHEN {RATE} IS NULL THEN
                          CASE
                            WHEN line IS NOT NULL THEN CASE
                              WHEN line.rate IS NULL THEN 0
                              ELSE line.rate
                            END
                            ELSE
                              CASE WHEN b.default_rate IS NULL THEN 0
                              ELSE b.default_rate
                            END
                          END
                        ELSE {RATE}
                      END
                    })
                CREATE (i)-[:ISSUED]->(iou)-[:HELDBY]->(b)
                RETURN iou
                ''',
                ISSUER_HANDLE=request.form['issuer'],
                BEARER_HANDLE=request.form['bearer'],
                ID=uuid(),
                DATE=request.form.get('issued_at') or datetime.datetime.now().isoformat(),
                VAL=int(request.form['value']),
                RATE=float(request.form['rate']) if request.form.get('rate') else None
            )
            return redirecdt('/ious/' + r.rows[0].iou['id'])

    return locals()[request.method.lower()]()

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(days=1000)

if __name__ == '__main__':
    app.run(host='0.0.0.0')
