from flask import Flask, redirect, request, Response
from g4f.client import Client
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import json
from datetime import datetime
import speech_recognition as sr
import requests
import subprocess
import os
import os.path
from g4f.cookies import set_cookies_dir, read_cookie_files
import asyncio
import g4f.debug
g4f.debug.logging = False

if os.name == "nt":
  asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

mon_app = Flask(__name__)
CORS(mon_app, origins="https://www.projet-voltaire.fr")
mon_client = Client()
if os.path.exists("har_and_cookies"):
  dossier_cookies = os.path.join(os.path.dirname(__file__), "har_and_cookies")
  set_cookies_dir(dossier_cookies)
  read_cookie_files(dossier_cookies)
reconnaissance = sr.Recognizer()

@mon_app.errorhandler(HTTPException)
def gerer_exception(erreur):
    reponse = erreur.get_response()
    reponse.data = json.dumps({
      "status": erreur.code,
      "message": erreur.name,
      "description": erreur.description,
    })
    reponse.content_type = "application/json"
    return reponse

@mon_app.route("/robots.txt")
def fichier_robots():
  """Cette route renvoie le fichier robots.txt."""
  reponse = Response("User-agent: *\nDisallow:")
  reponse.content_type = "text/plain"
  return reponse

@mon_app.route("/")
def accueil():
  """Cette route redirige vers le dépôt GitHub du projet."""
  return redirect("https://github.com/Shyphem/Voltaire", code=301)

@mon_app.route("/nearest-word", methods=["POST"])
def trouver_mot_proche():
  if not request.json or "word" not in request.json or "nearest_words" not in request.json:
    reponse = Response(json.dumps({
      "status": 400,
      "message": "Bad Request",
      "description": "La requête doit être un JSON avec une clé \"word\" et une clé \"nearest_words\"."
    }), status=400, content_type="application/json")
    raise HTTPException("Bad Request", response=reponse)

  mot: str = request.json["word"]
  mots_proches: list = request.json["nearest_words"]

  question = "Quel est le mot le plus proche de \"{}\" parmi : {}. Répond en json avec une clé \"word\".".format(mot, ", ".join(mots_proches))
  resultat_proche = json.loads(mon_client.chat.completions.create(
    model="gpt-4",
    response_format={ "type": "json_object" },
    messages=[{
      "role": "user", "content": question
    }],
    max_tokens=500,
  ).choices[0].message.content)

  return Response(json.dumps({
    "word": resultat_proche['word'],
  }), content_type="application/json")

@mon_app.route("/put-word", methods=["POST"])
def completer_mot_manquant():
  if not request.json or "sentence" not in request.json or "audio_url" not in request.json:
    reponse = Response(json.dumps({
      "status": 400,
      "message": "Bad Request",
      "description": "La requête doit être un JSON avec une clé \"sentence\" et une clé \"audio_url\"."
    }), status=400, content_type="application/json")
    raise HTTPException("Bad Request", response=reponse)

  phrase: str = request.json["sentence"]
  if "{}" not in phrase:
    reponse = Response(json.dumps({
      "status": 400,
      "message": "Bad Request",
      "description": "La phrase doit contenir un \"{}\" pour placer le mot manquant."
    }), status=400, content_type="application/json")
    raise HTTPException("Bad Request", response=reponse)
  url_audio: str = request.json["audio_url"]
  if "  " in phrase:
    phrase = phrase.replace("  ", " {} ")

  fichier_audio = requests.get(url_audio)
  nom_fichier_audio = os.path.abspath("./audio{}.mp3".format(datetime.timestamp(datetime.now())))
  nom_fichier_wav = nom_fichier_audio[:-3] + 'wav'
  with open(nom_fichier_audio, "wb") as f:
    f.write(fichier_audio.content)
  subprocess.run(['ffmpeg', '-i', nom_fichier_audio, nom_fichier_wav])

  with sr.AudioFile(nom_fichier_wav) as source:
    audio = reconnaissance.record(source)

  texte_reconnu: str = reconnaissance.recognize_google(audio, language="fr-FR")
  try:
    indice_mot_manquant = phrase.split(" ").index("{}")
  except ValueError:
    indice_mot_manquant = phrase.split(" ").index("{}.")
  mot_manquant = texte_reconnu.split()[indice_mot_manquant]
  phrase_complete = phrase.replace("{}", mot_manquant)

  os.remove(nom_fichier_audio)
  os.remove(nom_fichier_wav)

  return Response(json.dumps({
    "sentence": phrase,
    "fixed_sentence": phrase_complete,
    "missing_word": mot_manquant,
  }), content_type="application/json")

@mon_app.route("/intensive-training", methods=["POST"])
def entrainement_intensif():
  if not request.json or "sentences" not in request.json or "rule" not in request.json:
    reponse = Response(json.dumps({
      "status": 400,
      "message": "Bad Request",
      "description": "La requête doit être un JSON avec une clé \"sentences\" et une clé \"rule\"."
    }), status=400, content_type="application/json")
    raise HTTPException("Bad Request", response=reponse)

  phrases = request.json["sentences"]
  regle = request.json["rule"]
  #question = "Suivant la règle : \"{}\" Les phrases :\n- {}\nSont elles correctes ? Répond avec du JSON avec un tableau d'objets qui prend comme clés \"sentence\" pour la phrase et la clé \"correct\" si cette dernière est correcte.".format(regle, "\n- ".join(phrases))
  question = ("Les phrases :\n- {}\nSont elles correctes ? Répond avec un tableau JSON qui prend comme valeur un boolean"
            " si cette dernière est correcte (sous le format [true, false, true]).".format("\n- ".join(phrases)))
  reponse_api = mon_client.chat.completions.create(
    model="gpt-4",
    response_format={"type": "json_object"},
    messages=[{
      "role": "user", "content": question
    }],
    max_tokens=500,
  )
  donnees_json = json.loads(reponse_api.choices[0].message.content)
  return Response(json.dumps(donnees_json), content_type="application/json")

@mon_app.route("/fix-sentence", methods=["POST"])
def corriger_phrase():
  if not request.json or "sentence" not in request.json:
    reponse = Response(json.dumps({
      "status": 400,
      "message": "Bad Request",
      "description": "La requête doit être un JSON avec une clé \"sentence\"."
    }), status=400, content_type="application/json")
    raise HTTPException("Bad Request", response=reponse)

  maintenant = datetime.now()
  phrase = request.json["sentence"]
  question = ("Corrige les fautes dans cette phrase : \"{}\". Répond avec du JSON avec la clé \"word_to_click\" avec "
            "comme valeur le mot non corrigé qui a été corrigé, ou null s'il n'y a pas de fautes.").format(phrase)
  reponse_api = mon_client.chat.completions.create(
    model="gpt-4",
    response_format={"type": "json_object"},
    messages=[{
      "role": "user", "content": question
    }],
    max_tokens=500,
  )
  donnees_json = json.loads(reponse_api.choices[0].message.content)
  return Response(json.dumps({
    "word_to_click": donnees_json["word_to_click"],
    "time_taken": (datetime.now() - maintenant).total_seconds(),
  }), content_type="application/json")