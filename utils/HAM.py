import requests

class HAM(): 

	def __init__(self, apikey):
		self.host = "https://api.harvardartmuseums.org"
		self.apikey = apikey

	def search(self, type, filters={}, size=10, page=1, fields="", sort=""):
		url = "{host}/{endpoint}".format(host=self.host, endpoint=type)
		query = {
			"apikey": self.apikey,
			"size": size,
			"page": page,
			"fields": fields,
			"sort": sort
		}
		response = requests.get(url, params={**query, **filters})

		return response.json()

	def get(self, type, id):
		url = "{host}/{endpoint}/{id}".format(host=self.host, endpoint=type, id=id)
		qs = {"apikey": self.apikey}
		response = requests.get(url, params=qs)

		return response.json()