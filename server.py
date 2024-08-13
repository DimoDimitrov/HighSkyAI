#The following integration is acheved by sinchrous programming. Flask doest directly work with async, so we can use Quart for upgrading it.

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import asyncio

from enchanced_agent import bongoAgent

app = Flask(__name__)
CORS(app)

@app.route('/api/response', methods=['POST'])
def response():
    query = request.json
    result = bongoAgent(query)
    return jsonify({'result': result})

if __name__ == "__main__":
    app.run(debug=True)
