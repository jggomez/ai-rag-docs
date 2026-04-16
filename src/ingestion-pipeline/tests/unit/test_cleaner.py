import pytest
from src.filters.cleaner import document_cleaner

def test_document_cleaner_basic():
    raw_text = """
    CONSORCIO EINGETEC / SEDIC
    NIT. 890.900.123-1
    Calle 7 Sur No. 42-70
    MEDELLIN - COLOMBIA
    
    Asunto: NOTIFICACIÓN DE INICIO DE OBRA FRENTE 5
    
    Estimados señores:
    
    Por medio de la presente informamos que el día 20 se dará inicio 
    a las labores en el frente 5.
    
    Página 1 de 1
    
    Atentamente,
    
    ING. JUAN PEREZ
    Firma Digital: abc-1234-def5
    """
    
    result = document_cleaner(raw_text)
    
    assert result["subject"] == "NOTIFICACIÓN DE INICIO DE OBRA FRENTE 5"
    assert "Por medio de la presente informamos" in result["body_clean"]
    assert "Página 1 de 1" not in result["body_clean"]
    assert "NIT. 890.900.123-1" not in result["body_clean"]

def test_ocr_paragraph_repair():
    raw_text = """
    Estimados señores:
    
    Esta es una línea que continúa
    en la siguiente línea sin punto final.
    
    Este es un nuevo párrafo. que termina.
    Y esta es otra línea.
    
    Atentamente,
    """
    
    result = document_cleaner(raw_text)
    
    # "línea que continúa en la siguiente línea" should be joined
    assert "línea que continúa en la siguiente línea" in result["body_clean"]
    assert "Este es un nuevo párrafo." in result["body_clean"]
