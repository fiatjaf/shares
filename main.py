import settings

import datetime
import timestring
import neo4j
from neo4j.manager import ConnectionManager

import timestring
import dateutil.parser

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

@app.route('/lines/<granter>/->/<receiver>/', methods=['GET', 'PUT'])
@app.route('/lines/', methods=['GET', 'POST'])
def lines(granter=None, receiver=None):
    if granter and receiver:
        def get():
            r = graph.request('''
                MATCH (g:Agent {handle:{GRANTER_HANDLE}})
                MATCH (r:Agent {handle:{RECEIVER_HANDLE}})
                MATCH (g)-[l:GRANTS]->(r)
                RETURN g, l, r
            ''',
                GRANTER_HANDLE=granter,
                RECEIVER_HANDLE=receiver
            )

            line = r.rows[0].l
            line['granter'] = granter
            line['receiver'] = receiver

            return jsonify(line)
        def put():
            pass
    else:
        def get():
            r = graph.request('''
                MATCH (g)-[l:GRANTS]->(r)
                RETURN g, l, r
            ''')

            lines = []
            for row in r.rows:
                line = row.l
                line['granter'] = row.g['handle']
                line['receiver'] = row.r['handle']
                lines.append(line)

            return jsonify({'lines': lines})
        def post():
            granter = request.form['granter']
            receiver = request.form['receiver']
            r = graph.request('''
                MATCH (g:Agent {handle:{GRANTER_HANDLE}})
                MATCH (r:Agent {handle:{RECEIVER_HANDLE}})
                MERGE (g)-[line:GRANTS]->(r)
                ON CREATE SET line.value = {VAL}
                            , line.rate = {RATE}
                ON MATCH SET  line.value = {VAL}
                            , line.rate = {RATE}
                RETURN line
            ''',
                GRANTER_HANDLE=granter,
                RECEIVER_HANDLE=receiver,
                VAL=int(request.form.get('value') or 0),
                RATE=float(request.form.get('rate') or 0)
            )
            return redirect('/lines/' + granter + '/->/' + receiver)

    return locals()[request.method.lower()]()

@app.route('/paths/<granter>/->/<receiver>/', methods=['GET'])
def paths(granter, receiver):
    r = graph.request('''
        MATCH (g:Agent {handle:{GRANTER_HANDLE}})
        MATCH (r:Agent {handle:{RECEIVER_HANDLE}})
        MATCH fullpath = (g)-[:GRANTS*..10]->(r)
        WITH fullpath, relationships(fullpath) as path, nodes(fullpath) as agents
        WITH agents, path, extract(a in tail(agents) | a.handle) as names
        WITH names, path, reduce(r = 0, line in path | r + line.rate) as rate
        RETURN path, names, rate ORDER BY rate
    ''',
        GRANTER_HANDLE=granter,
        RECEIVER_HANDLE=receiver
    )

    paths = []
    for row in r.rows:
        path = {
            'length': len(row.names),
            'rate': row.rate,
            'through': row.names
        }
        paths.append(path)

    return jsonify({'paths': paths})

@app.route('/ious/<owes>/->/<to>/', methods=['POST', 'GET'])
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

            # interest calculation
            issuance = dateparse(iou['issued_at'])
            today = datetime.date.today()
            days_passed = (today - issuance).days
            daily_rate = float(1 + iou['rate']/100)**(1.0/4380)
            amount = iou['value'] * (daily_rate**days_passed)
            iou['total_owed_today'] = amount
            iou['interest'] = amount - iou['value']

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
                OPTIONAL MATCH (b)-[line:GRANTS]->(i)
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
                DATE=(dateparse(request.form.get('issued_at')) or datetime.date.today()).isoformat(),
                VAL=int(request.form['value']),
                RATE=float(request.form['rate']) if request.form.get('rate') else None
            )
            return redirect('/ious/' + r.rows[0].iou['id'])

    return locals()[request.method.lower()]()

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(days=1000)

## utils
def dateparse(string):
    try:
        return timestring.Date(string).date.date()
    except timestring.TimestringInvalid:
        try:
            return dateutil.parser.parse(string).date()
        except ValueError:
            return None

if __name__ == '__main__':
    app.run(host='0.0.0.0')
