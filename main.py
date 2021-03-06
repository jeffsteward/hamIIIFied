#!/usr/bin/env python3

import os
import tweepy
import requests
import configparser
import html2text
from PIL import Image
from utils.HAM import HAM
from random import randint

config = configparser.ConfigParser()
config.read('config.ini')

ham = HAM(config["HAM"]["API_KEY"])

iiifImageFragmentURLTemplate = "%s/%s/full/0/native.jpg"
hamShortURLTemplate = "http://hvrd.art/o/%s"

def main():
	""" Main entry point of the app """
	if not os.path.exists("temp"):
		os.makedirs("temp")

	random = randint(0,3)
	if random == 0:
		(filename, message) = make_text_collage(randint(4,8))

	elif random == 1:
		(filename, message) = make_face_collage(randint(4,6))

	elif random == 2:
		(filename, message) = make_face()

	else: 
		(filename, message) = make_guerrilla()

	tweet_it(filename, message)


def tweet_it(filename, message):
	auth = tweepy.OAuthHandler(config["TWITTER"]["CONSUMER_KEY"], config["TWITTER"]["CONSUMER_SECRET"])
	auth.set_access_token(config["TWITTER"]["ACCESS_TOKEN"], config["TWITTER"]["ACCESS_TOKEN_SECRET"])

	api = tweepy.API(auth)
	api.update_with_media(filename=filename, status=message)


def make_face():
	data = ham.search("annotation", filters={"q": "body:VERY_UNLIKELY"}, size=1, sort="random")
	annotation = data["records"][0]

	image = ham.get("image", annotation["imageid"])
	obj = get_object_by_idsid(annotation["idsid"])

	fragment = annotation["selectors"][0]["value"]

	imageURL = iiifImageFragmentURLTemplate % (image["iiifbaseuri"], fragment[5:])
	filename = 'temp/temp.jpg'
	request = requests.get(imageURL, stream=True)
	if request.status_code == 200:
		with open(filename, 'wb') as image:
			for chunk in request:
				image.write(chunk)

	message = "The machine says:\n" + html2text.html2text(annotation["body"]) + " " + hamShortURLTemplate % str(obj["id"])

	return filename, message


def make_text_collage(size=4):
	filters = {
		"q": "type:text"
	}
	data = ham.search("annotation", filters=filters, size=size, sort="random")
	annotations = data["records"]

	images = []
	phrases = []
	urls = []

	for annotation in annotations:
		# get more info about the image the annotation is on
		annotation["image"] = ham.get("image", annotation["imageid"])

		# get more info about the object that the image is of
		annotation["object"] = get_object_by_idsid(annotation["idsid"])

		# clean up annotations in the form "<p>age: 28<br/>gender: Female</p>"
		if "<br/>" in annotation["body"]:
			phrase = annotation["body"].replace("<p>age: ","")
			phrase = phrase.replace("<br/>gender: ", " year old ")
			phrase = phrase.replace("</p>","")
			phrases.append(phrase.lower())
		else:
			phrases.append(annotation["body"])

		if "id" in annotation["object"]: 
			urls.append(hamShortURLTemplate % str(annotation["object"]["id"]))

		# rework some of data
		fragment = annotation["selectors"][0]["value"]
		region = fragment[5:]

		imageURL = iiifImageFragmentURLTemplate % (annotation["image"]["iiifbaseuri"], region)

		filename = 'temp/file-%s.jpg' % str(annotation["id"])
		request = requests.get(imageURL, stream=True)
		if request.status_code == 200:
			with open(filename, 'wb') as image:
				for chunk in request:
					image.write(chunk)

			images.append(Image.open(filename))

	# make the collage image
	collage = append_images(images, direction='vertical', aligment='left')
	collage.save("temp/collage.jpg", "jpeg")

	message = "The machine writes from %s:\n\n %s" % (", ".join(urls), " ".join(phrases))

	return "temp/collage.jpg", message

def make_face_collage(size=4):
	data = ham.search("annotation", filters={"q": "type:face"}, size=size, sort="random")
	annotations = data["records"]
	
	for annotation in annotations:
		# get more info about the image the annotation is on
		annotation["image"] = ham.get("image", annotation["imageid"])

		# get more info about the object that the image is of
		annotation["object"] = get_object_by_idsid(annotation["idsid"])
		if "id" in annotation["object"]:
			annotation["shorturl"] = hamShortURLTemplate % str(annotation["object"]["id"])
		else: 
			annotation["shorturl"] = ""

		# rework the xywh data in the fragment
		fragment = annotation["selectors"][0]["value"]
		coords = fragment[5:]
		parts = coords.split(",")
		annotation["width"] = parts[2]
		annotation["height"] = parts[3]

	# sort the images from shortest to tallest
	sorted_annotations = sorted(annotations, key=lambda k: int(k["height"]))

	# split the sorted list in two and reassemble to form a pyramid-ish distribution of slices
	#  ***                **
	# ***** rather than  ***
	#  ***              ****
	left_half = sorted_annotations[0::2]
	right_half = sorted_annotations[1::2]
	right_half.reverse()
	collage_annotations = left_half + right_half

	images = []
	offset = 25

	for x, annotation in enumerate(collage_annotations):
		# calculate the slice of the fragment
		fragment = annotation["selectors"][0]["value"]
		coords = fragment[5:]
		parts = coords.split(",")
		width = int(parts[2])/size
		padding = (offset if (int(parts[0]) > offset) else 0)
		parts[0] = str(int(parts[0]) + int(width * x) - int(padding/2))
		parts[2] = str(int(width) + padding)
		coords = ",".join(parts)

		imageURL = iiifImageFragmentURLTemplate % (annotation["image"]["iiifbaseuri"], coords)

		filename = 'temp/file-%s.jpg' % str(x)
		request = requests.get(imageURL, stream=True)
		if request.status_code == 200:
			with open(filename, 'wb') as image:
				for chunk in request:
					image.write(chunk)

			images.append(Image.open(filename))

	combo_1 = append_images(images, direction='horizontal')
	combo_1.save("temp/collage.jpg", "jpeg")

	url_list = ", ".join([d["shorturl"] for d in annotations])

	message = "The machine makes collages from %s:\n" % (url_list)

	return "temp/collage.jpg", message

def make_guerrilla():
	ggMaskImageURL = "https://ids.lib.harvard.edu/ids/iiif/400595669"
	ggMaskRegion = "89,61,1119,1715"
	images = []

	data = ham.search("annotation", filters={"q": "type:face"}, size=1, sort="random")
	annotations = data["records"]
	
	# get the main image
	filename = 'temp/file-%s.jpg' % str(annotations[0]["imageid"])	
	request = requests.get(annotations[0]["target"], stream=True)
	if request.status_code == 200:
		with open(filename, 'wb') as image:
			for chunk in request:
				image.write(chunk)

		images.append(Image.open(filename))

	# get the position of the face
	fragment = annotations[0]["selectors"][0]["value"]
	coords = fragment[5:]
	parts = coords.split(",")

	# size the guerrilla mask
	ggImage = ggMaskImageURL + "/" + ggMaskRegion + "/" + parts[2] + ",/0/native.jpg"
	request = requests.get(ggImage, stream=True)
	ggFilename = "temp/file-gg.jpg"
	if request.status_code == 200:
		with open(ggFilename, 'wb') as image:
			for chunk in request:
				image.write(chunk)
				
		images.append(Image.open(ggFilename))

	# create the collage
	images[0].paste(images[1], (int(parts[0]), int(parts[1])))
	images[0].save("temp/collage-gg.jpg", "jpeg")

	message = "The guerrillas strike again:"

	return "temp/collage-gg.jpg", message

def append_images(images, direction='horizontal',
                  bg_color=(255,255,255), aligment='center'):
    """
    Appends images in horizontal/vertical direction.

    Args:
        images: List of PIL images
        direction: direction of concatenation, 'horizontal' or 'vertical'
        bg_color: Background color (default: white)
        aligment: alignment mode if images need padding;
           'left', 'right', 'top', 'bottom', or 'center'

    Returns:
        Concatenated image as a new PIL image object.
    """
    widths, heights = zip(*(i.size for i in images))

    if direction=='horizontal':
        new_width = sum(widths) - 75
        new_height = max(heights)
    else:
        new_width = max(widths)
        new_height = sum(heights)

    new_im = Image.new('RGB', (new_width, new_height), color=bg_color)

    offset = 0
    for im in images:
        if direction=='horizontal':
            y = 0
            if aligment == 'center':
                y = int((new_height - im.size[1])/2)
            elif aligment == 'bottom':
                y = new_height - im.size[1]
            new_im.paste(im, (offset, y))
            offset += im.size[0] - 25
        else:
            x = 0
            if aligment == 'center':
                x = int((new_width - im.size[0])/2)
            elif aligment == 'right':
                x = new_width - im.size[0]
            new_im.paste(im, (x, offset))
            offset += im.size[1]

    if aligment == 'center':
        y = int((new_height - images[0].size[1])/2)
        new_im.paste(images[0], (0, y))


    return new_im


def get_object_by_idsid(idsid):
	filters = {
		"q": "images.idsid:" + str(idsid)
	}

	data = ham.search("object", filters=filters, size=1)
	if len(data["records"]) > 0:
		return data["records"][0]
	else:
		return []


if __name__ == "__main__":
    """ This is executed when run from the command line """
    main()
