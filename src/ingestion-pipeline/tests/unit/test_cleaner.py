from src.filters.cleaner import document_cleaner, DocumentCleaner
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentStatus
from src.domain.enums import DocumentType


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
    assert "Esta es una línea que continúa en la siguiente línea sin punto final." in result["body_clean"]
    assert "Este es un nuevo párrafo. que termina." in result["body_clean"]


def test_cleaner_noise_patterns():
    raw_text = """
    Estimados señores:
    
    TEL: 1234567
    Avenida 10 # 5-2
    INT-OC-CYS-1283/25
    INGENIEROS CONSULTORES
    Radicado por: Juan Perez
    Radicado EPM 876543
    
    Esta es la única línea real del documento.
    
    Atentamente,
    """
    result = document_cleaner(raw_text)
    
    # All noise lines should be eliminated
    assert "TEL: 1234567" not in result["body_clean"]
    assert "Avenida 10" not in result["body_clean"]
    assert "INT-OC-CYS-1283/25" not in result["body_clean"]
    assert "INGENIEROS CONSULTORES" not in result["body_clean"]
    assert "Radicado por" not in result["body_clean"]
    assert "Radicado EPM" not in result["body_clean"]
    assert "Esta es la única línea real del documento." in result["body_clean"]


def test_cleaner_digital_signatures():
    raw_text = """
    Estimados señores:
    
    Texto principal.
    1709283748 10:25
    a1b2c3d4-e5f6-a7b8-c9d0-1234567890ab
    
    Atentamente,
    """
    result = document_cleaner(raw_text)
    
    assert "1709283748" not in result["body_clean"]
    assert "a1b2c3d4" not in result["body_clean"]
    assert "Texto principal." in result["body_clean"]


def test_cleaner_bullet_lists_not_joined():
    raw_text = """
    Estimados señores:
    
    Puntos a discutir:
    1. Primer punto
    2. Segundo punto
    • Tercer punto con viñeta
    - Cuarto punto
    
    Atentamente,
    """
    result = document_cleaner(raw_text)
    
    # Bullet points and numbered items should remain on new lines
    lines = result["body_clean"].split('\n')
    assert any(line.startswith("1. Primer punto") for line in lines)
    assert any(line.startswith("2. Segundo punto") for line in lines)
    assert any(line.startswith("• Tercer punto") for line in lines)
    assert any(line.startswith("- Cuarto punto") for line in lines)


def test_cleaner_spacing_normalization():
    raw_text = """
    Estimados señores:
    
    Texto  con   múltiples    espacios.
    
    
    
    Párrafo separado por tres saltos.
    
    Atentamente,
    """
    result = document_cleaner(raw_text)
    
    assert "Texto con múltiples espacios." in result["body_clean"]
    assert "\n\n\n" not in result["body_clean"]


def test_document_cleaner_filter_class():
    doc = SourceDocument(
        id="test", filename="test.pdf", bucket="b", object_name="obj",
        content_type="pdf", size_bytes=0, status=DocumentStatus.PROCESSING,
        document_type=DocumentType.RECEIVED, sender="S", contract_number="C",
        work_front="W", document_date="D", process="P",
        metadata={"extracted_text": "Estimados señores:\n\nHola mundo.\n\nAtentamente,"}
    )
    payload = ProcessingPayload(document=doc)
    filter_instance = DocumentCleaner()
    
    res = filter_instance.process(payload)
    self_text = res.document.metadata["extracted_text"]
    self_sub = res.document.metadata["document_subject"]
    
    assert self_text == "Hola mundo."
    assert self_sub == "Not detected"


def test_document_cleaner_filter_class_empty_payload():
    doc = SourceDocument(
        id="test", filename="test.pdf", bucket="b", object_name="obj",
        content_type="pdf", size_bytes=0, status=DocumentStatus.PROCESSING,
        document_type=DocumentType.RECEIVED, sender="S", contract_number="C",
        work_front="W", document_date="D", process="P",
        metadata={}
    )
    payload = ProcessingPayload(document=doc)
    filter_instance = DocumentCleaner()
    
    res = filter_instance.process(payload)
    assert "extracted_text" not in res.document.metadata
