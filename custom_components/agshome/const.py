"""Constantes pour l'intégration AGSHome Alarm."""

DOMAIN = "agshome"

# Config
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_HOST = "host"
CONF_PROTOCOL = "protocol_version"
CONF_CAMERA_HOST = "camera_host"
CONF_CAMERA_DEVICE_ID = "camera_device_id"
CONF_CAMERA_LOCAL_KEY = "camera_local_key"

# Signaux
SIGNAL_UPDATE = "agshome_update"
SIGNAL_ZONE_UPDATE = "agshome_zone_update"
SIGNAL_CAMERA_UPDATE = "agshome_camera_update"

# Protocole Tuya par défaut
DEFAULT_PROTOCOL = "3.3"
DEFAULT_PORT = 6668

# ─────────────────────────────────────────────────────────────
# DPS — Centrale alarme AGSHome (hub principal)
# Sources : tuya-local #907, #1059 ; localtuya #1383
# ─────────────────────────────────────────────────────────────

DP_MASTER_STATE    = 1   # enum  : disarmed|armed_away|armed_home|sos|triggered
DP_BATTERY_LEVEL   = 2   # int   : 0–100 %
DP_SENSOR_COUNT    = 3   # int   : nb capteurs appairés
DP_SIREN_ACTIVE    = 4   # bool  : sirène en cours
DP_TAMPER          = 6   # bool  : sabotage boîtier
DP_AC_POWER        = 10  # bool  : alimentation secteur OK
DP_ALARM_TRIGGERED = 12  # bool  : alarme déclenchée
DP_READY           = 13  # bool  : système prêt
DP_WIFI_OK         = 27  # bool  : WiFi OK
DP_COUNTDOWN       = 28  # int   : compte à rebours entrée/sortie (s)

# DP 26 : Zone déclenchée (base64 UTF-16LE → texte lisible)
# Ex. décodé : "System Alarm\nZone: 001"
DP_ZONE_TRIGGERED  = 26

# DP 32 : Dernier état capteur  → "normal" | "alarm" | "triggered"
DP_LAST_SENSOR_STATE = 32

# DP 36 : Type sous-appareil ayant déclenché
# Valeurs : "remote_controller"|"door_sensor"|"pir"|"sos_button"|...
DP_SUB_CLASS       = 36

# DP 37 : Numéro de zone (int)
DP_ZONE_NUMBER     = 37

# DP 101 : État détaillé  → "1"=désarmé | "2"=away | "3"=home
DP_DETAILED_STATE  = 101

# ─────────────────────────────────────────────────────────────
# DPS — Caméra AGSHome WiFi (device indépendant Tuya)
# ─────────────────────────────────────────────────────────────

DP_CAM_MOTION      = 115  # bool  : mouvement détecté
DP_CAM_ONLINE      = 1    # bool  : caméra en ligne
DP_CAM_LIGHT       = 101  # bool  : LED nuit allumée
DP_CAM_FLIP        = 103  # bool  : image retournée
DP_CAM_WATERMARK   = 108  # bool  : filigrane date/heure
DP_CAM_SD_STATUS   = 110  # enum  : état carte SD
DP_CAM_NIGHTVISION = 109  # enum  : mode vision nocturne (auto|color|night)

# ─────────────────────────────────────────────────────────────
# Mapping types sous-appareils Tuya → classes HA
# ─────────────────────────────────────────────────────────────

SUB_CLASS_TO_HA = {
    "door_sensor":         "door",
    "pir":                 "motion",
    "pir_sensor":          "motion",
    "motion_sensor":       "motion",
    "smoke_sensor":        "smoke",
    "water_sensor":        "moisture",
    "sos_button":          "safety",
    "remote_controller":   None,   # télécommande → on n'en fait pas d'entité
    "keyboard":            None,
}

# Mapping état Tuya → HA AlarmControlPanel
TUYA_TO_HA_STATE = {
    "disarmed":   "disarmed",
    "armed_away": "armed_away",
    "armed_home": "armed_home",
    "arm":        "armed_away",
    "sos":        "triggered",
    "triggered":  "triggered",
    "alarm":      "triggered",
    "1": "disarmed",
    "2": "armed_away",
    "3": "armed_home",
}

# Mapping commandes HA → valeurs Tuya DP1
HA_TO_TUYA_CMD = {
    "disarm":   "disarmed",
    "arm_away": "armed_away",
    "arm_home": "armed_home",
}

# Plateformes exposées
PLATFORMS = ["alarm_control_panel", "binary_sensor", "sensor", "switch", "camera"]
