from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from config import AZURE_LANGUAGE_KEY, AZURE_LANGUAGE_ENDPOINT


def _get_client():
    credential = AzureKeyCredential(AZURE_LANGUAGE_KEY)
    return TextAnalyticsClient(endpoint=AZURE_LANGUAGE_ENDPOINT, credential=credential)


def analizar_texto(texto):
    client = _get_client()

    resp_sent = client.analyze_sentiment(documents=[texto])[0]
    sentimiento = resp_sent.sentiment.upper()

    resp_ner = client.recognize_entities(documents=[texto])[0]
    entidades = [e.text for e in resp_ner.entities]

    return {
        "sentimiento": sentimiento,
        "entidades":   entidades,
    }