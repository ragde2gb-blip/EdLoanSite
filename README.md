# My Lending (Web)

A Philippine-peso lending management web application, rebuilt from the original
CustomTkinter desktop app. It runs a local web server (Flask) with SQLite storage
and an admin login, and is accessed through any browser — on the same PC, or from
other devices on your network.

## Run on Windows

```powershell
cd path\to\my_lending_web
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The first time it runs, you'll be asked to create the admin account (username +
password). After that, every screen requires signing in. Sessions are stored
server-side; use **Sign out** in the top bar to end your session, and **Account**
to change your password.

All loans and payments are stored automatically in `my_lending.db`, created next
to the app files on first run.

## Using it on other devices

By default the app only listens on `127.0.0.1` (this PC only). To reach it from
your phone or another computer on the same network, edit the last line of
`app.py`:

```python
app.run(host="0.0.0.0", port=5000, debug=False)
```

Then visit `http://<this-PC's-LAN-IP>:5000` from the other device. Only do this
on networks you trust — anyone who can reach that address and knows the admin
password can view and edit your lending records.

## Features

- **Dashboard** — active borrowers, principal released, total receivable, and
  payments collected at a glance, plus the most recent loans.
- **New Loan** — enter borrower, contact, principal, monthly interest, and term.
  Total interest is calculated as `principal × (monthly interest % / 100) × months`.
- **Borrowers** — search by name, contact, or loan ID. Open a profile to see
  principal, interest, total payment, payments received, and running balance.
  Rename or delete a borrower's loan record (deleting also removes its payment
  history and cannot be undone).
- **Payments** — record a repayment against any active loan; view full payment
  history.
- **Export** — download borrower records as CSV or Excel (`.xlsx`) from the
  Borrowers page.

## Notes

- The admin password is stored as a salted hash (never in plain text).
- A random session secret key is generated on first run and stored in
  `instance/secret_key` — keep this file private and don't commit it if you
  put the project under version control.
