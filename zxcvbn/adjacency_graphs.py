
import pkg_resources
import json

data = pkg_resources.resource_string(__name__, 'generated/adjacency_graphs.json')
adjacency_graphs = json.loads(data.decode())

