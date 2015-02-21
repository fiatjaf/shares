import os

DEBUG = os.getenv('DEBUG') in ['True', 'true', '1', 'yes']
SECRET_KEY = os.getenv('SECRET_KEY') or 'asdbaskdb'

GRAPHENEDB_URL = os.getenv('GRAPHENEDB_URL')
MAILGUN_API_KEY = os.getenv('MAILGUN_API_KEY')

SERVICE_NAME = os.getenv('SERVICE_NAME') or 'ripple'
SERVICE_URL = os.getenv('SERVICE_URL') or 'http://ripple.alhur.es/'
CONTACT_EMAIL = os.getenv('CONTACT_EMAIL') or 'team@ripple.alhur.es'
