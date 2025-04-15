from flask import Flask, request, jsonify, render_template, session
from phi.agent import Agent
from phi.model.groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-20q-key")

# Initialize the Groq Agent
agent = Agent(
    model=Groq(id="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY"))
)

# Route to load the main webpage
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle POST chat requests
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip().lower()

    # Instructions to the AI agent (system prompt)
    system_prompt = (
        "You are the guesser in a game of 20 Questions. The user is thinking of an object, and you must figure it out "
        "by asking one yes-or-no question at a time. You must remember what you’ve already asked. "
        "NEVER repeat any question. Do not ask the same thing in different wording. "
        "Your questions should narrow the search intelligently. When confident, make a guess like 'Is it a banana?'. "
        "Once you make a guess, wait for the user to confirm (yes or no) and do not ask more questions until told to restart."
    )

    if user_input == "restart":
        session.pop("qa", None)
        session.pop("guess_made", None)
        return jsonify({"response": "Game restarted. Let's begin!\n\nIs it a living thing?"})

    if user_input == "start":
        session["qa"] = [{"question": "Is it a living thing?", "answer": None}]
        session["guess_made"] = False
        return jsonify({"response": "Is it a living thing?"})

    # Prevent interaction if game hasn't started
    if "qa" not in session or not session["qa"]:
        return jsonify({"response": "Please type 'start' to begin the game."})

    # Handle post-guess confirmation
    if session.get("guess_made", False):
        if user_input in ["yes", "y"]:
            session.pop("qa", None)
            session.pop("guess_made", None)
            return jsonify({"response": "Yay! I got it right \n\nType 'start' to play again."})
        elif user_input in ["no", "n"]:
            session.pop("qa", None)
            session.pop("guess_made", None)
            return jsonify({"response": "Aw, I missed \n\nType 'start' to try again!"})
        else:
            return jsonify({"response": "Please answer 'yes' or 'no' to my guess, or type 'restart' to begin again."})

    # Store user's answer
    qa = session.get("qa", [])
    if qa[-1]["answer"] is None:
        qa[-1]["answer"] = user_input
        session["qa"] = qa
    else:
        return jsonify({"response": "Please wait for the next question. Type 'restart' if needed."})

    # Format prompt with history
    qa_lines = [f"- {item['question']} {item['answer']}" for item in qa if item["answer"]]
    question_count = len(qa_lines)
    remaining = 20 - question_count

    # Construct prompt for the agent with context
    prompt = (
        f"You have asked {question_count} questions. You have {remaining} left.\n"
        f"These are the questions and answers so far:\n"
        f"{chr(10).join(qa_lines)}\n\nAsk your next yes/no question. "
        f"If you’re very confident, guess the object."
    )

    try:
        response_obj = agent.run(prompt, system=system_prompt)
        next_question = response_obj.content.strip()

        # Detect guess (starts with 'is it', 'i guess', etc.)
        if any(next_question.lower().startswith(phrase) for phrase in ["is it", "i guess", "is the object"]):
            session["guess_made"] = True
            return jsonify({
                "response": f"{next_question}\n\nAm I right? (yes/no)"
            })

        # Avoid duplicate questions
        asked_questions = [q["question"].lower() for q in qa if q.get("question")]
        if next_question.lower() in asked_questions:
            next_question += " (Try asking something else!)"

        # Store the new question
        qa.append({"question": next_question, "answer": None})
        session["qa"] = qa

    # Return the next question to user
    except Exception as e:
        next_question = f"Error: {e}"

    # Run the app in debug mode
    return jsonify({"response": next_question})

if __name__ == '__main__':
    app.run(debug=True)
