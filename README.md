# 🚨 AGSHome Alarm — Intégration Home Assistant

Intégration Home Assistant pour la centrale d'alarme **AGSHome** (WiFi, protocole **Tuya local**), compatible HACS.

Connexion **100% locale** — aucun cloud requis après la configuration initiale.

---

## ✅ Entités créées

| Entité | Type | Description |
|---|---|---|
| `alarm_control_panel.agshome_alarme` | Alarme | Armé / Désarmé / Armé partiel / Déclenché |
| `binary_sensor.agshome_sabotage` | Capteur | Sabotage de la centrale |
| `binary_sensor.agshome_sirene_active` | Capteur | Sirène en cours |
| `binary_sensor.agshome_alimentation_secteur` | Capteur | Prise secteur présente |
| `binary_sensor.agshome_alarme_declenchee` | Capteur | Alarme en cours |
| `binary_sensor.agshome_systeme_pret` | Capteur | Système prêt |
| `binary_sensor.agshome_wifi_connecte` | Capteur | Connectivité WiFi |
| `sensor.agshome_batterie_de_secours` | Capteur | Niveau batterie (%) |
| `sensor.agshome_compte_a_rebours` | Capteur | Timer entrée/sortie (s) |
| `sensor.agshome_capteurs_connectes` | Capteur | Nombre de capteurs |

---

## 📋 Prérequis

- Home Assistant OS ou Supervised (**2023.1.0+**)
- HACS installé
- Centrale AGSHome connectée à votre réseau WiFi via l'app **Smart Life**
- **IP fixe** assignée à la centrale dans votre box/routeur
- **Device ID** et **Local Key** Tuya (procédure ci-dessous)

---

## 🔑 Étape 1 — Obtenir le Device ID et la Local Key

> ⚠️ Cette étape est **indispensable**. La Local Key est la clé de chiffrement locale de votre centrale. Elle change si vous ré-appairez l'appareil dans Smart Life.

### 1.1 — Créer un compte Tuya IoT

1. Rendez-vous sur **[iot.tuya.com](https://iot.tuya.com)**
2. Créez un compte (différent du compte Smart Life)
3. À la fin de l'inscription, choisissez **Individual Developer**

### 1.2 — Créer un projet Cloud

1. Dans le menu gauche : **Cloud** → **Development** → **Create Cloud Project**
2. Remplissez :
   - **Project Name** : n'importe quoi (ex: "Home Assistant")
   - **Industry** : Smart Home
   - **Development Method** : Smart Home
   - **Data Center** : choisissez **Central Europe** ou la région la plus proche
3. Cliquez sur **Create**
4. Dans la fenêtre suivante, cliquez sur **All** pour autoriser tous les services API, puis **Authorize**

### 1.3 — Lier votre compte Smart Life

1. Dans votre projet, allez dans l'onglet **Devices** → **Link Tuya App Account**
2. Cliquez sur **Add App Account**
3. Ouvrez l'app **Smart Life** sur votre téléphone
4. Appuyez sur le **+** ou l'icône de scan
5. Scannez le QR code affiché sur l'écran Tuya IoT
6. Validez sur votre téléphone

### 1.4 — Récupérer Device ID et Local Key

1. Dans votre projet Tuya IoT, allez dans **Devices** → **All Devices**
2. Vous devriez voir votre centrale AGSHome listée
3. Notez le **Device ID** (colonne "Device ID")
4. Cliquez sur l'icône **ℹ️** ou sur le device
5. Notez la **Local Key** (champ "Local key" ou "local_key")

> 💡 **Alternative avec TinyTuya** (si la Local Key n'est pas visible sur le portail) :
> ```bash
> pip install tinytuya
> python -m tinytuya wizard
> ```
> Suivez l'assistant, il récupère automatiquement tous vos devices et leurs Local Keys.

---

## 🚀 Installation via HACS

### Étape 2 — Ajouter le dépôt

1. Dans Home Assistant : **HACS** → **Intégrations**
2. Menu **⋮** → **Dépôts personnalisés**
3. URL : `https://github.com/H0ros/HA_AGSHome`
4. Catégorie : `Intégration`
5. Cliquez **Ajouter**

### Étape 3 — Installer

1. **HACS** → **Intégrations** → cherchez **"AGSHome Alarm"**
2. Cliquez → **Télécharger**
3. **Redémarrez Home Assistant**

### Étape 4 — Configurer

1. **Paramètres** → **Appareils et services** → **+ Ajouter une intégration**
2. Cherchez **"AGSHome"**
3. Remplissez :

| Champ | Exemple | Description |
|---|---|---|
| Adresse IP | `192.168.1.42` | IP fixe de la centrale |
| Device ID | `bf1234abc...` | Copié depuis Tuya IoT |
| Local Key | `aB3dEf7g...` | Copié depuis Tuya IoT |
| Version protocole | `3.3` | Essayez 3.3 puis 3.4 |

---

## 🔧 Installation manuelle (sans HACS)

```bash
# Via SSH dans HA
cd /config/custom_components
git clone https://github.com/H0ros/HA_AGSHome.git temp
mv temp/custom_components/agshome .
rm -rf temp
# Redémarrer HA
```

---

## 🌐 Publier sur GitHub

```bash
git init ha-agshome && cd ha-agshome
# Copier les fichiers ici
git add .
git commit -m "feat: initial AGSHome integration"
git branch -M main
git remote add origin https://github.com/H0ros/HA_AGSHome.git
git push -u origin main
git tag v1.0.0 && git push origin v1.0.0
```

Remplacez `VOTRE_USERNAME` dans `manifest.json` et `hacs.json`.

---

## 🏠 Utilisation — Exemples d'automatisation

### Armer automatiquement la nuit

```yaml
automation:
  - alias: "Armer alarme la nuit"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: alarm_control_panel.alarm_arm_home
        target:
          entity_id: alarm_control_panel.agshome_alarme
```

### Notifier sur déclenchement

```yaml
automation:
  - alias: "Notification alarme déclenchée"
    trigger:
      - platform: state
        entity_id: alarm_control_panel.agshome_alarme
        to: "triggered"
    action:
      - service: notify.mobile_app_mon_telephone
        data:
          title: "🚨 ALARME DÉCLENCHÉE"
          message: "Votre alarme AGSHome s'est déclenchée !"
```

### Désarmer à l'arrivée

```yaml
automation:
  - alias: "Désarmer à l'arrivée"
    trigger:
      - platform: zone
        entity_id: device_tracker.mon_telephone
        zone: zone.home
        event: enter
    action:
      - service: alarm_control_panel.alarm_disarm
        target:
          entity_id: alarm_control_panel.agshome_alarme
```

---

## 🔍 Dépannage

### Erreur "cannot_connect"
→ Vérifiez que la centrale et HA sont sur le même réseau (même sous-réseau).  
→ Vérifiez l'IP fixe (la centrale peut avoir changé d'IP).  
→ Essayez la version protocole **3.4** au lieu de 3.3.  
→ Fermez l'app Smart Life sur votre téléphone (elle peut bloquer la connexion locale).

### La Local Key ne fonctionne plus
→ Si vous avez ré-appairé la centrale dans Smart Life, la Local Key a changé. Retournez sur iot.tuya.com pour récupérer la nouvelle.

### Les entités ne se mettent pas à jour
→ La centrale Tuya envoie des push — si l'app Smart Life est ouverte en parallèle, elle peut intercepter les messages. Fermez-la.

### Activer les logs détaillés

```yaml
logger:
  default: warning
  logs:
    custom_components.agshome: debug
```

---

## 🗺️ Mapping DPS AGSHome (référence technique)

| DP | Nom | Type | Valeurs |
|---|---|---|---|
| 1 | État principal | enum | `disarmed` / `armed_away` / `armed_home` / `triggered` / `sos` |
| 2 | Batterie secours | int | 0–100 (%) |
| 3 | Nb capteurs | int | nombre |
| 4 | Sirène | bool | true/false |
| 6 | Sabotage | bool | true/false |
| 10 | Alimentation secteur | bool | true/false |
| 12 | Alarme déclenchée | bool | true/false |
| 13 | Système prêt | bool | true/false |
| 27 | WiFi OK | bool | true/false |
| 28 | Compte à rebours | int | secondes |
| 32 | Dernier capteur | enum | `normal` / `triggered` |
| 101 | État détaillé | enum | `1`=off / `2`=away / `3`=home |

> Ces DPS sont communs aux alarmes Tuya de ce type. Si votre firmware expose des DPS différents, consultez les logs HA avec le niveau `debug` activé.

---

## 🏗️ Architecture

```
custom_components/agshome/
├── __init__.py              # Setup/unload
├── manifest.json            # Métadonnées HACS
├── const.py                 # Constantes & mapping DPS
├── config_flow.py           # UI de configuration
├── agshome_client.py        # Client Tuya local (TinyTuya)
├── coordinator.py           # Coordinateur HA
├── alarm_control_panel.py   # Centrale alarme
├── binary_sensor.py         # Sabotage, sirène, secteur…
├── sensor.py                # Batterie, compteur…
└── translations/
    ├── fr.json
    └── en.json
```

**Protocole** : Communication **Tuya LAN** (port 6668, AES-128 chiffré) via la bibliothèque [TinyTuya](https://github.com/jasonacox/tinytuya).

---

## 📄 Licence

MIT License
