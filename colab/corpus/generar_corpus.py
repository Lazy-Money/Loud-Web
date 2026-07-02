import re, random
random.seed(42)
import espeakng_loader
from phonemizer.backend import EspeakBackend
from phonemizer.backend.espeak.wrapper import EspeakWrapper
EspeakWrapper.set_library(espeakng_loader.get_library_path())
EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
backend = EspeakBackend('es', preserve_punctuation=False, with_stress=False)

ok = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ,.;:¿?¡!'\-]+$")
# Palabra "no nativa": tiene k/w, o dígrafos ajenos al español, o dobles no nativas
foreign = re.compile(r"[kwKW]|sh|sch|ck|tz|th|zh|ph|ss|ff|tt|pp|mm|bb|dd|gg|hh|yy")
NATIVE_DOUBLES = ("ll", "rr", "cc", "nn", "ee", "oo", "aa")  # permitidas

def is_native(word):
    w = word.lower()
    if any(ch in w for ch in "kw"): return False
    for dig in ("sh","sch","ck","tz","th","zh","ph","ss","ff","tt","pp","mm","bb","dd","gg","hh"):
        if dig in w and dig not in NATIVE_DOUBLES: return False
    return True

seen, pool = set(), []
for fn in ("sc.txt", "wiki.txt"):
    for line in open(fn, encoding="utf-8", errors="replace"):
        s = line.strip().strip('"').strip()
        if not (40 <= len(s) <= 140): continue
        if not ok.match(s): continue
        words = s.split()
        if not (6 <= len(words) <= 20): continue
        # rechazar si hay palabras no nativas
        if any(not is_native(w.strip(",.;:¿?¡!'-")) for w in words if len(w) > 2): continue
        # limitar nombres propios (mayúscula no inicial) a lo sumo 1
        caps = sum(1 for w in words[1:] if w[:1].isupper())
        if caps > 1: continue
        key = s.lower()
        if key in seen: continue
        seen.add(key); pool.append(s)
print(f"Pool nativo filtrado: {len(pool)} frases")

random.shuffle(pool)
sample = pool[:30000]
print("Fonemizando 30.000...")
phon = backend.phonemize(sample)
def diphones(p):
    chars = [c for c in "".join(p.split())]
    return set(zip(chars, chars[1:]))
cand = [(sample[i], diphones(phon[i])) for i in range(len(sample)) if phon[i].strip()]

TARGET = 1300
covered, chosen, sets = set(), [], cand[:]
while len(chosen) < TARGET and sets:
    bi, bg = -1, -1
    for i,(t,d) in enumerate(sets):
        g = len(d - covered)
        if g > bg: bg, bi = g, i
    t,d = sets.pop(bi); chosen.append(t); covered |= d
    if bg == 0 and len(chosen) >= 300:
        rem = [x for x,_ in sets]; random.shuffle(rem)
        chosen.extend(rem[:TARGET-len(chosen)]); break
random.shuffle(chosen)  # mezclar para que no queden las exóticas al principio
open("corpus_alex.txt","w",encoding="utf-8").write("\n".join(chosen)+"\n")
lens=[len(s) for s in chosen]
print(f"Seleccionadas: {len(chosen)} | difonemas: {len(covered)} | long media: {sum(lens)//len(lens)} car")
