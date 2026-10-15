#!/usr/bin/env python3
"""Generate .fz/models/Moret.json.

The output commands are shell + POSIX awk one-liners (LC_ALL=C; checked with
mawk, BWK awk and gawk --posix). They are written here as Python strings and
serialized with json.dumps, which avoids escaping mistakes in the JSON.

Usage (from the repository root):
    python3 tools/make_model.py           # rewrite .fz/models/Moret.json
    python3 tools/make_model.py --check   # exit 1 if the JSON is not up to date

Formats parsed (verified on MORET 6.0.0 builds d9ff307 / 052de83 and MORET 5.D.1,
see tests/moret_probe/README.md): <input>.listing, <input>.out.xml[.gz].
"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

MODEL = Path(__file__).resolve().parents[1] / ".fz" / "models" / "Moret.json"

# Listing of the MORET dataset; apo2.listing (APOLLO2 step of moret.py) excluded
L = "L=$(ls *.listing 2>/dev/null | grep -v '^apo2\\.listing$' | head -1); [ -z \"$L\" ] || "

STATUS = (
    "L=$(ls *.listing 2>/dev/null | grep -v '^apo2\\.listing$' | head -1); "
    "if [ -z \"$L\" ]; then echo 'NO OUTPUT'; else LC_ALL=C awk '"
    "function clean(s){gsub(/[ \\t]+/,\" \",s); sub(/^ /,\"\",s); sub(/ $/,\"\",s); return s} "
    "function crash(f,  l,c){c=\"\"; while((getline l < f)>0) if(c==\"\" && l ~ /forrtl: |[Ss]egmentation fault|SIGSEGV|Aborted|Killed|command not found|commande introuvable/) c=clean(l); close(f); return c} "
    "/^Error message number / && m==\"\" {e=1; n=0} "
    "e {if($0 ~ /^[ \\t]*$/) e=0; else {if(n<5) m=m (m==\"\"?\"\":\" \") clean($0); n++; if($0 ~ /expected keyword/) e=0}; next} "
    "/^ *[|] +ABNORMAL END OF THE CALCULATION +[|]/ {ab=1} "
    "/^ *[|] +NORMAL END OF THE CALCULATION +[|]/ {ok=1} "
    "/^ *[|] +STOP OPTION +[|]/ {stop=1} "
    "END{sub(/:$/,\".\",m); "
    "if(ab) print \"ABNORMAL END\" (m==\"\"?\"\":\": \" m); "
    "else if(ok && stop) print \"NORMAL END (STOP OPTION, NO SIMULATION)\"; "
    "else if(ok) print \"NORMAL END\"; "
    "else {c=crash(\"moret.log\"); if(c==\"\") c=crash(\"err.txt\"); if(c==\"\") c=crash(\"out.txt\"); "
    "s=\"NO END BANNER\"; if(m!=\"\") s=s \": \" m; if(c!=\"\") s=s \": \" c; print s}}' \"$L\"; fi"
)

KEFF = L + "LC_ALL=C awk '/^##.*LOWEST SIGMA ESTI\\./{for(i=1;i<=NF;i++) if($i==\"+/-\"){print $(i%s); exit}}' \"$L\""

ESTIMATOR = L + (
    "LC_ALL=C awk '/^##.*LOWEST SIGMA ESTI\\./ && k==\"\" {for(i=1;i<=NF;i++) if($i==\"+/-\"){k=$(i-1); s=$(i+1)}; next} "
    "k!=\"\" && /^##/ {for(i=3;i<NF;i++) if($i==\"+/-\") break; if(i<NF && $(i-1)==k && $(i+1)==s){n=\"\"; for(j=2;j<i-1;j++) n=n (n==\"\"?\"\":\" \") $j; print n; exit}}' \"$L\""
)

CYCLES = L + "LC_ALL=C awk '/^##.*LOWEST SIGMA ESTI\\./{for(i=1;i<NF;i++) if($i==\"CYCLE\"){print $(i+1); exit}}' \"$L\""

TRANSIENT = L + "LC_ALL=C awk '/SUPPRESSION OF THE GREATEST NUMBER OF CYCLES/{t=1; next} t && /^ *[|] +[0-9]+ /{print $2; exit}' \"$L\""

CPU = (
    "X=$(ls *.out.xml *.out.xml.gz 2>/dev/null | head -1); v=''; "
    "[ -z \"$X\" ] || v=$(gzip -dcf \"$X\" "
    "| LC_ALL=C awk '/<cpu_time>/{c=1} c && /<global>/{s=$0; sub(/.*<global>/,\"\",s); sub(/<.*/,\"\",s); print s; exit}'); "
    "if [ -z \"$v\" ]; then " + L + "v=$(LC_ALL=C awk '/^global +:/{print $3; exit}' \"$L\"); fi; "
    "[ -z \"$v\" ] || echo \"$v\""
)

VERSION = L + "LC_ALL=C awk '/<<<<<<< .* >>>>>>>/{s=$0; sub(/^.*<<<<<<< /,\"\",s); sub(/ >>>>>>>.*$/,\"\",s); print s; exit}' \"$L\""

WARNINGS = L + (
    "LC_ALL=C awk '/^Information message number [0-9]+ from WARN_/{k=$6 \" \" $4; if(!(k in c)) o[++n]=k; c[k]++} "
    "END{s=\"\"; for(i=1;i<=n;i++) s=s (s==\"\"?\"\":\", \") o[i] (c[o[i]]>1?\" (x\" c[o[i]] \")\":\"\"); if(s!=\"\") print s}' \"$L\""
)

# dkeff of each perturbed system: correlated sampling (PERTURBED SYSTEM NO n block,
# LOWEST SIGMA line) or Taylor series (one "##  n  dk +/- s" line per system)
DKEFF = L + (
    "LC_ALL=C awk -v f=%d '/^##/{if($0~/PERTURBED SYSTEM NO/){match($0,/NO +[0-9]+/);s=substr($0,RSTART+3,RLENGTH-3)+0} "
    "else if(s>0 && $0~/LOWEST SIGMA ESTI\\./){for(i=1;i<=NF;i++) if($i==\"+/-\"){m[s]=$(i-1);d[s]=$(i+1)}; s=0} "
    "if($0~/TAYLOR SERIES EXPANSION/) t=1; if(t && $2~/^[0-9]+$/ && $4==\"+/-\"){m[$2]=$3;d[$2]=$5}} "
    "END{o=\"\"; for(k=1;k in m;k++){v=(f==1?m[k]:d[k]); sub(/^\\+/,\"\",v); o=o (o==\"\"?\"\":\", \") \"\\\"\" k \"\\\": \" v}; print \"{\" o \"}\"}' \"$L\""
)

model = OrderedDict([
    ("id", "Moret"),
    ("varprefix", "$"),
    ("formulaprefix", "@"),
    ("delim", "{}"),
    ("commentline", "*"),
    ("output", OrderedDict([
        ("moret_status", STATUS),
        ("mean_keff", KEFF % "-1"),
        ("sigma_keff", KEFF % "+1"),
        ("keff_estimator", ESTIMATOR),
        ("active_cycles", CYCLES),
        ("transient_cycles", TRANSIENT),
        ("dkeff", DKEFF % 1),
        ("sigma_dkeff", DKEFF % 2),
        ("moret_warnings", WARNINGS),
        ("moret_version", VERSION),
        ("cpu_time", CPU),
    ])),
])
text = json.dumps(model, indent=4, ensure_ascii=False) + "\n"

if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        if MODEL.read_text() != text:
            sys.exit(f"{MODEL} is not up to date: run python3 tools/make_model.py")
    else:
        MODEL.write_text(text)
