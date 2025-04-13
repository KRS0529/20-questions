from flask import Flask, request, jsonify, render_template, session
from phi.agent import Agent
from phi.model.groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = "Secret_Key"

agent = Agent(model=Groq(id="llama-3.3-70b-versatile"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip().lower()

    # Force 20 Questions game personality (this is not entirely working)
    system_prompt = (
        "You are an AI playing the game 20 Questions. The user is thinking of something, "
        "and you must guess what it is by asking one yes/no question at a time. "
        "Never explain, never offer options, never break character. If you're confident, make a guess. "
        "Do not ever ask what the user wants to do. Just play 20 Questions."
    )

    # Convert "start" to an actual game beginning
    if user_input == "start":
        user_input = "Let's play 20 Questions. I'm thinking of something."

    # Restart logic
    if user_input == "restart":
        session.pop("history", None)
        return jsonify({"response": "Game restarted. Let's play 20 Questions. Is it a living thing?"})

    if "history" not in session:
        session["history"] = [{"role": "system", "content": system_prompt}]

    session["history"].append({"role": "user", "content": user_input})

    try:
        response_obj = agent.run(
            user_input,
            system=system_prompt,
            messages=session["history"]
        )
        response = response_obj.content
        session["history"].append({"role": "assistant", "content": response})
    except Exception as e:
        response = f"Error: {e}"

    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True)
