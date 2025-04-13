from flask import Flask, request, jsonify, render_template, session
from phi.agent import Agent
from phi.model.groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = "super-secret-20q-key"

agent = Agent(model=Groq(id="llama-3.3-70b-versatile"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()

    # Restart game if user types 'restart'
    if user_input.lower() == "restart":
        session.pop("history", None)
        return jsonify({"response": "Game restarted. Let's play 20 Questions! Is it a living thing?"})

    # System prompt — always use this
    system_prompt = (
        "You are an AI playing the game 20 Questions. The user is thinking of something. "
        "Your goal is to guess what it is by asking only yes/no questions. "
        "Never explain, never define, never ask open-ended questions. "
        "Ask only one yes/no question per turn. When confident, make a guess like: 'Is it a cat?'."
    )

    # If no history yet, simulate starting the game
    if "history" not in session:
        session["history"] = [
            {"role": "user", "content": "Let's play."}
        ]
        response_obj = agent.run("Let's play.", system=system_prompt)
        response = response_obj.content
        session["history"].append({"role": "assistant", "content": response})
        return jsonify({"response": response})

    # Normal gameplay — one question per turn
    try:
        response_obj = agent.run(user_input, system=system_prompt)
        response = response_obj.content
        session["history"].append({"role": "user", "content": user_input})
        session["history"].append({"role": "assistant", "content": response})
    except Exception as e:
        response = f"Error: {e}"

    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(debug=True)