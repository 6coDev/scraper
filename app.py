import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import os

# ========== CONFIGURATION ==========
CHROMEDRIVER_PATH = "chroma/chromedriver.exe" 

# ========== UI ==========
st.set_page_config(page_title="Scraper Réseaux Sociaux", layout="centered")
st.title("
         Scraper LinkedIn & Facebook")

site_choice = st.selectbox("Choisissez la plateforme à scraper", ["LinkedIn", "Facebook"])

with st.expander("Connexion requise"):
    email = st.text_input("Email", key="email_input")
    password = st.text_input("Mot de passe", type="password", key="password_input")

st.markdown("Entrez les URLs des profils à scraper")
url_input = st.text_area("Collez les URLs (une par ligne)", height=150)

uploaded_file = st.file_uploader("Ou importez un fichier `.csv` ou `.txt` avec les URLs", type=["csv", "txt"])

# ======= RÉCUPÉRATION DES URLS =======
profile_urls = []

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df_uploaded = pd.read_csv(uploaded_file)
        profile_urls = df_uploaded.iloc[:, 0].dropna().tolist()
    elif uploaded_file.name.endswith(".txt"):
        content = uploaded_file.read().decode("utf-8")
        profile_urls = [line.strip() for line in content.splitlines() if line.strip()]
elif url_input:
    profile_urls = [url.strip() for url in url_input.splitlines() if url.strip()]

# ======= SELENIUM CONFIG =======
def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-notifications")
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

# ======= FONCTIONS LOGIN & SCRAPE =======

def login_linkedin(driver, email, password):
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "username").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    time.sleep(5)

def scrape_linkedin(driver, url):
    driver.get(url)
    time.sleep(4)
    try:
        name = driver.find_element(By.CSS_SELECTOR, "h1.text-heading-xlarge").text.strip()
    except:
        name = "Nom introuvable"
    try:
        title = driver.find_element(By.CSS_SELECTOR, "div.text-body-medium.break-words").text.strip()
    except:
        title = "Poste introuvable"
    return [name, title, url]

def login_facebook(driver, email, password):
    driver.get("https://www.facebook.com/login")
    time.sleep(2)
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "pass").send_keys(password)
    driver.find_element(By.NAME, "login").click()
    time.sleep(5)

def scrape_facebook(driver, url, password_user):
    driver.get(url)
    time.sleep(4)
    try:
        full_name = driver.find_element(By.TAG_NAME, "h1").text.strip()
        # Séparation nom/prénom (simple, à adapter selon le format)
        parts = full_name.split(" ", 1)
        prenom = parts[0] if len(parts) > 0 else ""
        nom = parts[1] if len(parts) > 1 else ""
    except:
        prenom = ""
        nom = ""
        full_name = "Nom introuvable"
    try:
        photo_url = driver.find_element(By.XPATH, "//image[contains(@xlink:href,'profile')]").get_attribute("xlink:href")
    except:
        photo_url = "Photo non trouvée"
    try:
        ville = driver.find_element(By.XPATH, "//span[contains(text(),'Ville actuelle') or contains(text(),'Habite à')]/following-sibling::span").text.strip()
    except:
        ville = "Ville non trouvée"
    return [prenom, nom, url, photo_url, ville, password_user]

# ======= BOUTON SCRAPER =======
if st.button("🚀 Lancer le scraping"):
    if not email or not password:
        st.warning("Veuillez entrer vos identifiants.")
    elif not profile_urls:
        st.warning("Veuillez entrer au moins une URL.")
    else:
        driver = setup_driver()
        try:
            with st.spinner(f"Connexion à {site_choice}..."):
                if site_choice == "LinkedIn":
                    login_linkedin(driver, email, password)
                else:
                    login_facebook(driver, email, password)

            data = []
            for url in profile_urls:
                with st.spinner(f"Scraping {url}..."):
                    if site_choice == "LinkedIn":
                        data.append(scrape_linkedin(driver, url))
                    else:
                        data.append(scrape_facebook(driver, url, password))

            columns = (
                ["Nom", "Poste", "URL"] if site_choice == "LinkedIn"
                else ["Prénom", "Nom", "URL", "Photo de profil", "Ville", "Password utilisé"]
            )
            df = pd.DataFrame(data, columns=columns)

            st.success("✅ Scraping terminé")
            st.dataframe(df)

            csv_file = f"{site_choice.lower()}_profils.csv"
            df.to_csv(csv_file, index=False)

            with open(csv_file, "rb") as f:
                st.download_button("📥 Télécharger le CSV", f, file_name=csv_file)

        except Exception as e:
            st.error(f"❌ Erreur : {e}")
        finally:
            driver.quit()
            if os.path.exists(csv_file):
                os.remove(csv_file)
