# Deploying FraudShield

There are two free ways to put FraudShield online. Do Part 1 first, then Part 2 and/or Part 3.

| Option | What goes online | Cost | Time |
|---|---|---|---|
| **GitHub Pages** | Online demo dashboard (the model runs in the browser) | Free, always on | 5 min |
| **Render** | The full Python app + REST API | Free (sleeps when idle) | 10 min |
| IBM Cloud Code Engine (optional) | The full app in a Docker container on IBM Cloud | Free tier, needs a card | 20 min |

---

## Part 1: Upload the project to GitHub

1. Create a free account at **github.com** if you don't have one.
2. Click **+** (top right) → **New repository**.
   - Repository name: `FraudShield`
   - Choose **Public** (GitHub Pages is free only for public repos)
   - Do **not** tick "Add a README" (we already have one)
   - Click **Create repository**
3. On the next page, click the link **"uploading an existing file"**.
4. Open the unzipped `FraudShield` folder on your laptop, select **everything inside it**
   (Ctrl + A), and drag it into the browser window.
   - Hidden files like `.gitignore` may not show in File Explorer. In File Explorer, go to **View → Show → Hidden items** first,
     then select all.
5. Wait until all files finish uploading, write a message like `Initial commit`, and click **Commit changes**.
6. Check the repo page. You should see `app.py`, `src/`, `docs/`, `render.yaml`, `README.md` and the other files at the top level, **not** inside an extra
   `FraudShield/` folder. If they ended up inside a folder, delete the repo and upload again, dragging the folder's *contents*.

**Using Git instead (optional):**
```bash
cd FraudShield
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/FraudShield.git
git push -u origin main
```

---

## Part 2: GitHub Pages (online demo, always on)

1. In your repo, go to **Settings** → **Pages** (left sidebar).
2. Under **Build and deployment** → Source: **Deploy from a branch**.
3. Branch: **main**, folder: **/docs** → click **Save**.
4. Wait 1–2 minutes and refresh the page. A link appears at the top:
   `https://<your-username>.github.io/FraudShield/`
5. Open it. You should see the dashboard with transactions already in the live feed.

---

## Part 3: Render (full Python app + API)

1. Go to **render.com** → **Get Started** → sign up **with GitHub**.
2. Click **New +** → **Blueprint**.
3. Select your `FraudShield` repo (click **Configure account** if it isn't listed, and give Render access to it).
4. Render reads `render.yaml` automatically. Click **Apply** / **Deploy Blueprint**.
5. The build installs the libraries, generates the data and trains the model. That takes **about 3–6 minutes** on the free plan.
   Watch the **Logs** tab until you see `FraudShield running ->`.
6. Your app's link is shown at the top of the service page: `https://fraudshield-xxxx.onrender.com`

**If Blueprint doesn't work**, use **New +** → **Web Service** → pick the repo, and fill in:

| Field | Value |
|---|---|
| Runtime / Language | Python 3 |
| Build Command | `pip install -r requirements.txt && python src/data_generator.py && python src/train.py` |
| Start Command | `python app.py` |
| Instance Type | Free |
| Environment variable | `PYTHON_VERSION` = `3.11.9` |

**Test the live API:**
```bash
curl -X POST https://<your-app>.onrender.com/api/score -H "Content-Type: application/json" -d "{\"amount\":46000,\"old_balance\":50000,\"user_avg_amount\":1200,\"txn_type\":\"P2P_TRANSFER\",\"hour\":2,\"is_new_receiver\":true,\"is_new_device\":true}"
```

**Important:** free Render apps go to sleep after 15 minutes without visitors. The first visit after that takes
about 1 minute to wake up. **Open your link 2–3 minutes before your presentation.**

---

## Part 4 (optional): IBM Cloud Code Engine

Good if your evaluators want to see it running on IBM Cloud. You need an IBM Cloud account (free tier; it may ask for a card to verify).

1. Log in at **cloud.ibm.com** → search **Code Engine** → **Create project** (any region, for example Mumbai or Tokyo).
2. Inside the project → **Applications** → **Create**.
3. Choose **Build container image from source code**.
   - Source: your GitHub repo URL, branch `main`
   - Strategy: **Dockerfile** (the repo already has one)
4. Under **Image start options**, set listening port **8080**.
5. Resources: 1 vCPU / 2 GB is plenty. Min instances: 0.
6. Click **Create**. When the build finishes (around 5 minutes), open the application URL shown on the page.

---

## Updating after changes

- **Web upload:** open the file on GitHub → pencil icon → edit → **Commit changes**. Or use **Add file → Upload files** again.
- Render redeploys automatically after every commit. GitHub Pages updates within a minute or two.
- If you retrain the model and want the online demo to match, run `python src/export_web_model.py` and commit the `docs/` folder.

## Troubleshooting

| Problem | Fix |
|---|---|
| Pages link shows 404 | Wait 2 minutes. Check Settings → Pages says branch `main` and folder `/docs`, and the repo is Public |
| Pages shows the README instead of the dashboard | You picked `/ (root)`. Change it to `/docs` |
| Render build fails at `pip install` | Check the `PYTHON_VERSION` environment variable is `3.11.9` |
| Render says "No trained model found" | The Build Command is missing the `data_generator.py` and `train.py` steps |
| Render page takes long to load | It was asleep. Wait about 1 minute |
| Files are inside an extra folder on GitHub | Re-upload the *contents* of the folder, not the folder itself |
