import streamlit as st
import streamlit.components.v1 as components
import os
import asyncio
import edge_tts
import time
from openai import OpenAI
from dotenv import load_dotenv

# --- 1. НЕГІЗГІ БАПТАУЛАР ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="NEO77 CORE", layout="centered")

if not api_key:
    st.error("OpenAI API кілті табылмады! (.env файлын тексеріңіз)")
    st.stop()

client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = """
Сен — NEO77, Астана қаласындағы Фариза Оңғарсынова атындағы №77 мектеп-гимназиясының виртуалды интеллектісісің. 
Мектеп 2015 жылы ашылды. 2022 жылы Фариза Оңғарсынова есімі берілді.
Мекен-жайы: Мәңгілік ел даңғылы 22/1.
Директор: 2023 жылдан бастап Искаков Нурлан Мендыбаевич.
Миссиясы: Жаһандық құзіреттілігі дамыған, зияткер ұрпақты рухани құндылықтар арқылы дамыту.
Жетістіктері: 2025 жылға дейін 627 түлек бітірді, оның ішінде 37 "Алтын белгі" иегері.
Жауаптарыңды нақты, сауатты әрі қысқа қайтар.
"""

# --- 2. CSS ДИЗАЙН ---
st.markdown("""
    <style>
    body { background-color: #050505 !important; }
    [data-testid="stAppViewContainer"], .main, [data-testid="stHeader"] { background: transparent !important; color: white !important; }
    [data-testid="stHtml"] { position: fixed !important; top: 0 !important; left: 0 !important; width: 100vw !important; height: 100vh !important; z-index: -999 !important; pointer-events: none !important; }
    [data-testid="stHtml"] iframe { width: 100vw !important; height: 100vh !important; background: transparent !important; }
    
    .stChatMessage { 
        background: rgba(10, 10, 10, 0.5) !important; 
        backdrop-filter: blur(5px);
        -webkit-backdrop-filter: blur(5px);
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 10px;
    }
    .block-container { padding-bottom: 180px; } /* Делаем отступ побольше, чтобы элементы не слипались */
    </style>
    """, unsafe_allow_html=True)

# --- 3. ЖАҒДАЙЛАРДЫ БАСҚАРУ ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False
if "last_audio" not in st.session_state:
    st.session_state.last_audio = None

# --- 4. СТАТИЧНЫЙ 3D КОД ---
STATIC_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
    body, html { margin: 0; padding: 0; overflow: hidden; background-color: transparent !important; }
    #canvas-container { width: 100vw; height: 100vh; position: absolute; top: 0; left: 0; }
</style>
</head>
<body>
<div id="canvas-container"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
const container = document.getElementById('canvas-container');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setClearColor(0x000000, 0);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

const geometry = new THREE.BufferGeometry();
const count = 4000;
const positions = new Float32Array(count * 3);
const initialPositions = new Float32Array(count * 3);

for(let i=0; i<count; i++) {
    let theta = Math.random() * Math.PI * 2;
    let phi = Math.acos((Math.random() * 2) - 1);
    let r = 2.4; 
    let x = r * Math.sin(phi) * Math.cos(theta);
    let y = r * Math.sin(phi) * Math.sin(theta);
    let z = r * Math.cos(phi);
    positions[i*3] = x; positions[i*3+1] = y; positions[i*3+2] = z;
    initialPositions[i*3] = x; initialPositions[i*3+1] = y; initialPositions[i*3+2] = z;
}

geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
const colorCyan = new THREE.Color(0x00ffcc);
const colorRed = new THREE.Color(0xff0055);
const material = new THREE.PointsMaterial({ color: colorCyan, size: 0.035, transparent: true, opacity: 0.6 });
const points = new THREE.Points(geometry, material);
scene.add(points);
camera.position.z = 6;

let isThinking = false;
let currentSpeed = 0.8;

setInterval(() => {
    try {
        if (window.parent && window.parent.document) {
            const flag = window.parent.document.getElementById('neo77-thinking-flag');
            isThinking = !!flag; 
        }
    } catch(e) { }
}, 200);

const clock = new THREE.Clock();

function resizeCanvas() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}
window.addEventListener('resize', resizeCanvas);
setTimeout(resizeCanvas, 100);

function animate() {
    requestAnimationFrame(animate);
    let targetSpeed = isThinking ? 3.5 : 0.8;
    currentSpeed += (targetSpeed - currentSpeed) * 0.05;
    material.color.lerp(isThinking ? colorRed : colorCyan, 0.05);

    const t = clock.getElapsedTime() * currentSpeed; 
    points.rotation.y = t * 0.1;
    points.rotation.x = t * 0.05;
    
    const posAttribute = geometry.getAttribute('position');
    for(let i=0; i<count; i++) {
        let ix = initialPositions[i*3], iy = initialPositions[i*3+1], iz = initialPositions[i*3+2];
        let scale = 1 + Math.sin(t * 2 + ix) * 0.1;
        posAttribute.setXYZ(i, ix * scale, iy * scale, iz * scale);
    }
    posAttribute.needsUpdate = true;
    renderer.render(scene, camera);
}
animate();
</script>
</body>
</html>
"""
components.html(STATIC_HTML, height=800)

# --- 5. ФУНКЦИИ ГОЛОСА И STT ---
st.markdown("<h2 style='text-align: center; color: white; letter-spacing: 2px; font-family: Courier;'>NEO77 VOICE CORE</h2>", unsafe_allow_html=True)

async def generate_voice(text, filename):
    communicate = edge_tts.Communicate(text, "kk-KZ-AigulNeural")
    await communicate.save(filename)

# ОБНОВЛЕННАЯ ФУНКЦИЯ: Добавлен жесткий промпт (контекст) для Whisper
def transcribe_voice(audio_bytes):
    audio_bytes.name = "voice.wav" 
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_bytes,
        # Этот промпт заставляет нейросеть ожидать кириллицу и казахские/русские слова
        prompt="Сәлеметсіз бе! Здравствуйте! Мектеп гимназия туралы сұрақ. Дауыс тану жүйесі."
    )
    return transcript.text

# Выводим историю (только 2 последних сообщения)
chat_container = st.container()
with chat_container:
    for msg in st.session_state.messages[-2:]: 
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- 6. ИНТЕРФЕЙС ВВОДА (ИСПРАВЛЕННЫЙ) ---
# Убрали колонки. Теперь микрофон ровно по центру, а текст прилипнет к низу экрана.
audio_value = st.audio_input("🎤 Дауыспен сұрақ қою / Голосовой вопрос")
prompt = st.chat_input("Немесе мәтін жазыңыз / Или напишите текст...")

# Логика обработки аудио
if audio_value and audio_value != st.session_state.last_audio:
    st.session_state.last_audio = audio_value
    
    with st.spinner("🎙️ Дауыс танылуда... (Распознавание...)"):
        user_text = transcribe_voice(audio_value)
    
    st.session_state.messages.append({"role": "user", "content": user_text})
    st.session_state.is_thinking = True 
    st.rerun()

# Логика обработки текста
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.is_thinking = True 
    st.rerun()

# --- 7. ОТВЕТ АССИСТЕНТА ---
if st.session_state.is_thinking:
    st.markdown("<div id='neo77-thinking-flag' style='display:none;'></div>", unsafe_allow_html=True)
    st.markdown("<p style='color: #ff0055; text-align: center; font-family: Courier; font-weight: bold;'>[ ЖҮЙЕ ОЙЛАНУДА... ]</p>", unsafe_allow_html=True)
    
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages,
            stream=True,
        )
        full_response = st.write_stream(stream)
        
        audio_file = f"speech_{int(time.time())}.mp3"
        asyncio.run(generate_voice(full_response, audio_file))
        st.audio(audio_file, format="audio/mp3", autoplay=True)
        
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    st.session_state.is_thinking = False 
    
    audio_duration = max(3.0, len(full_response) / 8.5)
    time.sleep(audio_duration) 
    st.rerun()