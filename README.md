# Who's The Jefe

A small office simulation where you run a design agency. Your employees live in a pixel-art office, work at their
desks, talk to each other and send you emails, and you answer them. Their emails, conversations and replies are
written by Claude.

Prototype (v0.1), built in May 2026. Case study: https://dev.luitiescobar.com/work/whos-the-jefe/

## How it works

- `simulator/simulator.py` moves the world forward in 5-second ticks (8 ticks per working day). Each employee has a
  role, skills, traits and a nationality, and their routines are staggered so the office never changes all at once.
  It writes the state to `simulator/state.json`.
- Claude Haiku is only called for events that matter: an email to the boss, a conversation between two employees,
  a reply to something you wrote. Cooldowns keep it from flooding the inbox.
- `simulator/server.py` is a small HTTP API on port 3001 for the inbox and your replies.
- `frontend/` is a Phaser 4 page that draws the office, sorts sprites by depth and shows speech bubbles in an
  HTML layer.

## Run it

You need Python 3, Node.js and an Anthropic API key.

```bash
pip install anthropic python-dotenv
echo ANTHROPIC_API_KEY=your-key > .env
cd frontend && npm install && cd ..
```

Then, in three terminals from the repo root:

```bash
python simulator/simulator.py
```

```bash
python simulator/server.py
```

```bash
npx serve . -p 3000
```

Open http://localhost:3000/frontend

The pixel-art sprites (`assets/`) are not included in this repository, so the office renders without them.

## Author

Luiti Escobar · https://dev.luitiescobar.com
