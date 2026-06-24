# Monthly Overtime — Working-Day Calculator

Streamlit app that computes net working days in an Indian (Karnataka default) month after deducting **gazetted public holidays + RBI 2nd/4th Saturday bank-closure Saturdays + developer leaves**, suited for an end-of-month overtime note to your manager.

## Run locally

```bash
cd ~/repos/leave-calc
source .venv/bin/activate
streamlit run app.py --server.port 8501 --server.headless true
```

Open http://localhost:8501

##Expose via Cloudflare quick tunnel (no account, free, ephemeral URL)

In a second terminal:

```bash
cloudflared tunnel --url http://localhost:8501
```

It prints a `https://<random>.trycloudflare.com` URL — share it. Keep both terminals running.

## Customize

- State: change the dropdown in Step 1, or edit `DEFAULT_STATE` in `app.py`.
- Weekend policy (5- vs 6-day): edit `WEEKEND_DAYS` in `app.py`. For 6-day week use `(6,)` (Sunday only).
- Half-day leaves: not supported in this build (integer arithmetic only).