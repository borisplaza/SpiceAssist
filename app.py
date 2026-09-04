import json, os, sqlite3, uuid, re
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DB_PATH = os.path.join(BASE_DIR, 'data', 'spiceassist.db')

FAQS = [
    {
        'intent':'product_info',
        'keywords':['producto','especia','condimento','pimienta','comino','oregano','mostaza','ajo','cebolla','coriandro','producto disponible','catalogo','catálogo'],
        'answer':'Puedo orientarte sobre productos, presentaciones y requisitos de compra. Indícame el producto o especia de interés y la cantidad aproximada para registrar la solicitud comercial.'
    },
    {
        'intent':'documents',
        'keywords':['coa','certificado','fitosanitario','fito','venta libre','spec','especificacion','especificación','documentos','certificaciones','certificado de origen'],
        'answer':'Según el tipo de operación, se pueden requerir documentos técnicos o regulatorios. Puedo registrar una solicitud para COA, especificación, certificado fitosanitario, certificado de venta libre u otro documento. La disponibilidad y el costo deben confirmarse antes de comprometerlos al cliente.'
    },
    {
        'intent':'pricing',
        'keywords':['precio','costo','cotizacion','cotización','tarifa','valor','cuanto cuesta','cuánto cuesta','payment','pago'],
        'answer':'Los precios dependen del producto, presentación, volumen y condiciones comerciales. Para evitar cotizaciones desactualizadas, registraré tu producto y cantidad para que el equipo comercial confirme precio, vigencia y forma de pago.'
    },
    {
        'intent':'payment',
        'keywords':['pago','wire','zelle','cash','tarjeta','credito','crédito','forma de pago','invoice','factura'],
        'answer':'Las condiciones de pago se validan según el tipo de cliente y la orden. Puedo registrar tu consulta para que el equipo confirme las opciones disponibles, cualquier recargo aplicable y las condiciones de crédito.'
    },
    {
        'intent':'delivery',
        'keywords':['delivery','entrega','envio','envío','despacho','retirar','pickup','warehouse','bodega','lead time','tiempo de entrega'],
        'answer':'El tiempo y modalidad de entrega dependen de disponibilidad, destino, volumen y hora de confirmación. Puedo registrar destino, producto y cantidad para que Operaciones confirme la opción adecuada.'
    },
    {
        'intent':'support',
        'keywords':['reclamo','queja','incidencia','problema','calidad','foreign object','bugs','devolucion','devolución','rechazo','soporte'],
        'answer':'Para incidencias de calidad o servicio, necesito identificar el producto, número de lote u orden, descripción del problema y evidencia disponible. El caso se registra para revisión humana antes de definir una resolución.'
    },
    {
        'intent':'order_status',
        'keywords':['estado','status','orden','pedido','seguimiento','cuando llega','cuándo llega','factura','invoice'],
        'answer':'Puedo registrar una solicitud de seguimiento de orden. Indícame el número de orden o factura y, si lo tienes, el producto asociado. El equipo responsable verificará el estado antes de confirmar una fecha.'
    },
    {
        'intent':'contact',
        'keywords':['hablar','contacto','asesor','ventas','persona','representante','llamar','correo','email'],
        'answer':'Claro. Puedo recopilar tus datos para que un representante continúe la atención. Escribe: nombre, correo, teléfono y empresa. No necesitas compartir información sensible.'
    }
]

SENSITIVE_PATTERNS = [
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), 'SSN'),
    (re.compile(r'\b(?:\d[ -]*?){13,16}\b'), 'posible tarjeta'),
]


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.executescript('''
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            contact_id INTEGER,
            intent TEXT NOT NULL,
            product TEXT,
            quantity TEXT,
            order_reference TEXT,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Nuevo',
            created_at TEXT NOT NULL,
            FOREIGN KEY(contact_id) REFERENCES contacts(id)
        );
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            intent TEXT,
            confidence REAL,
            created_at TEXT NOT NULL
        );
        ''')


def db_execute(sql, params=()):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid


def db_query(sql, params=()):
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def normalize(text):
    return re.sub(r'[^a-z0-9áéíóúñü ]+', ' ', text.lower()).strip()


def classify_intent(text):
    t = normalize(text)
    priority = [
        ('pricing',['cotizacion','cotización','precio','cuanto cuesta','cuánto cuesta']),
        ('order_status',['estado de la orden','status de la orden','seguimiento de orden','cuando llega','cuándo llega']),
        ('support',['reclamo','incidencia','queja','problema de calidad']),
        ('documents',['fitosanitario','certificado','coa','spec','documentos']),
        ('delivery',['delivery','entrega','envio','envío','despacho']),
        ('payment',['forma de pago','zelle','wire','tarjeta','crédito','credito'])
    ]
    for intent, phrases in priority:
        if any(normalize(p) in t for p in phrases):
            faq = next((f for f in FAQS if f['intent']==intent), None)
            return intent, 1.0, faq
    best = ('general', 0.0, None)
    for faq in FAQS:
        score = 0.0
        for kw in faq['keywords']:
            nkw = normalize(kw)
            if nkw in t:
                score += 1.0 + min(len(nkw)/30.0, 0.6)
            else:
                score = max(score, SequenceMatcher(None, t, nkw).ratio() * 0.45)
        score = min(score, 1.0)
        if score > best[1]:
            best = (faq['intent'], score, faq)
    return best


def detect_sensitive(text):
    hits=[]
    for pattern, label in SENSITIVE_PATTERNS:
        if pattern.search(text):
            hits.append(label)
    return hits


def extract_fields(text):
    products = ['comino','pimienta blanca','pimienta','orégano','oregano','mostaza','ajo','cebolla','coriandro','hibisco','jengibre','nigella','lavanda','manzanilla']
    nt = normalize(text)
    product = next((p for p in products if normalize(p) in nt), None)
    email = re.search(r'[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}', text)
    phone = re.search(r'(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}', text)
    qty = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(lb|lbs|pounds|kg|kgs|kilograms|cases|cajas|bags|bolsas)\b', text, re.I)
    order_ref = re.search(r'\b(?:SO|DL|INV|AR)[- ]?\d{3,8}\b', text, re.I)
    return {
        'product': product,
        'email': email.group(0) if email else None,
        'phone': phone.group(0) if phone else None,
        'quantity': qty.group(0) if qty else None,
        'order_reference': order_ref.group(0) if order_ref else None,
    }


def build_reply(message, intent, confidence, faq):
    sensitive = detect_sensitive(message)
    if sensitive:
        return ('Por seguridad, no incluyas datos financieros o identificadores sensibles en el chat. '
                'Puedo continuar con información comercial básica como nombre, correo, teléfono, empresa, producto y número de orden.'), True
    if faq and confidence >= 0.35:
        extra = ''
        if intent in {'pricing','delivery','product_info'}:
            extra = ' Si deseas seguimiento, indícame producto, cantidad, nombre y correo.'
        elif intent in {'support','order_status'}:
            extra = ' Si deseas seguimiento, indícame número de orden/lote y un correo de contacto.'
        return faq['answer'] + extra, False
    return ('Puedo ayudarte con productos, documentos, cotizaciones, pagos, entregas, estado de órdenes o incidencias. '
            'Cuéntame qué necesitas y registraré la solicitud si requiere seguimiento humano.'), False


def log_interaction(session_id, role, message, intent=None, confidence=None):
    db_execute('INSERT INTO interactions(session_id,role,message,intent,confidence,created_at) VALUES(?,?,?,?,?,?)',
               (session_id, role, message, intent, confidence, now_iso()))


def create_request_if_needed(session_id, intent, message, fields):
    if intent in {'pricing','delivery','support','order_status','documents','contact','product_info','payment'}:
        return db_execute('''INSERT INTO requests(session_id,intent,product,quantity,order_reference,message,status,created_at)
                          VALUES(?,?,?,?,?,?,'Nuevo',?)''',
                          (session_id, intent, fields.get('product'), fields.get('quantity'), fields.get('order_reference'), message, now_iso()))
    return None

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = urlparse(path).path
        if path == '/':
            path = '/index.html'
        return os.path.join(STATIC_DIR, path.lstrip('/'))

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        def do_GET(self):
        if self.path.startswith('/api/health'):
            return self._json(200, {'status':'ok','time':now_iso()})
        if self.path.startswith('/api/requests'):
            rows = db_query('SELECT id,session_id,intent,quantity,order_reference,status,created_at FROM requests ORDER BY id DESC LIMIT 50')
            return self._json(200, {'rows':rows})
        if self.path == '/':
            self.path = '/index.html'
        return super().do_GET()

    def do_POST(self):
        length = int(self.headers.get('Content-Length','0'))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw or '{}')
        except Exception:
            return self._json(400, {'error':'JSON inválido'})

        if self.path == '/api/chat':
            message = str(data.get('message','')).strip()
            session_id = str(data.get('session_id') or uuid.uuid4())
            if not message:
                return self._json(400, {'error':'Mensaje vacío'})
            log_interaction(session_id,'user',message)
            intent, confidence, faq = classify_intent(message)
            fields = extract_fields(message)
            reply, blocked = build_reply(message,intent,confidence,faq)
            request_id = None if blocked else create_request_if_needed(session_id,intent,message,fields)
            log_interaction(session_id,'assistant',reply,intent,confidence)
            return self._json(200, {
                'session_id':session_id,
                'reply':reply,
                'intent':intent,
                'confidence':round(confidence,3),
                'request_id':request_id,
                'captured':fields,
                'human_review_required': intent in {'pricing','delivery','support','order_status','documents','payment'}
            })

        if self.path == '/api/contact':
            session_id = str(data.get('session_id') or uuid.uuid4())
            name = str(data.get('name','')).strip()
            email = str(data.get('email','')).strip()
            phone = str(data.get('phone','')).strip()
            company = str(data.get('company','')).strip()
            if not (name and email):
                return self._json(400, {'error':'Nombre y correo son obligatorios'})
            if not re.match(r'^[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}$', email):
                return self._json(400, {'error':'Correo no válido'})
            contact_id = db_execute('INSERT INTO contacts(name,email,phone,company,created_at) VALUES(?,?,?,?,?)',
                                    (name,email,phone,company,now_iso()))
            db_execute('UPDATE requests SET contact_id=? WHERE session_id=? AND contact_id IS NULL', (contact_id,session_id))
            return self._json(200, {'ok':True,'contact_id':contact_id})
        return self._json(404, {'error':'Ruta no encontrada'})


def main():
    init_db()
    host='0.0.0.0'; port=int(os.environ.get('PORT','8000'))
    print(f'SpiceAssist disponible en http://{host}:{port}')
    ThreadingHTTPServer((host,port), Handler).serve_forever()

if __name__=='__main__':
    main()
