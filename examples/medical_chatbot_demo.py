#!/usr/bin/env python3
"""
Medical Chatbot Demo with AgentDebugger Context Management
==========================================================

This demo creates a medical chatbot using LangChain with Gemini API,
integrated with AgentDebugger's context management system for the web portal.

Features:
- Medical chatbot with LangChain and Gemini
- Context management for medical conversations
- Web portal integration
- Medical knowledge context storage
- Patient conversation history
- Medical advice context tracking
"""

import os
import time
import threading
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json

# LangChain imports
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.prompts import ChatPromptTemplate
    from langchain.schema import HumanMessage, AIMessage
    from langchain.callbacks.base import BaseCallbackHandler
except ImportError:
    print(
        "❌ LangChain not installed. Install with: pip install langchain langchain-google-genai"
    )
    exit(1)

# AgentDebugger imports
from agent_debugger import AgentDebugger
from agent_debugger.context import ContextType, ContextPriority
from agent_debugger.web import WebPortalDebugger, attach_agent_to_web


class MedicalContextCallback(BaseCallbackHandler):
    """Callback handler to capture medical context from LangChain interactions"""

    def __init__(self, debugger: AgentDebugger, patient_id: str):
        self.debugger = debugger
        self.patient_id = patient_id
        self.conversation_context = []

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs):
        """Capture LLM start for context management"""
        prompt = prompts[0] if prompts else ""

        # Add conversation context
        self.debugger.add_context(
            type=ContextType.CONVERSATION,
            key=f"patient_query_{int(time.time())}",
            value=prompt,
            priority=ContextPriority.HIGH,
            tags=["medical", "patient", "query"],
            agent_id=self.patient_id,
            metadata={"timestamp": datetime.now().isoformat(), "type": "patient_query"},
        )

    def on_llm_end(self, response: Any, **kwargs):
        """Capture LLM end for context management"""
        if hasattr(response, "generations") and response.generations:
            generation = response.generations[0][0]
            medical_response = generation.text

            # Add medical advice context
            self.debugger.add_context(
                type=ContextType.KNOWLEDGE,
                key=f"medical_advice_{int(time.time())}",
                value=medical_response,
                priority=ContextPriority.CRITICAL,
                tags=["medical", "advice", "response"],
                agent_id=self.patient_id,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "type": "medical_advice",
                },
            )


class MedicalChatbot:
    """Medical chatbot with LangChain and Gemini integration"""

    def __init__(self, patient_id: str, debugger: AgentDebugger, gemini_api_key: str):
        self.patient_id = patient_id
        self.debugger = debugger
        self.gemini_api_key = gemini_api_key
        self.conversation_history = []

        # Initialize Gemini LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.7,
            max_output_tokens=1024,
        )

        # Create medical prompt template
        self.medical_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a helpful medical assistant. You can provide general health information, 
            suggest when to see a doctor, and offer lifestyle advice. However, you cannot:
            - Provide specific medical diagnoses
            - Prescribe medications
            - Replace professional medical advice
            
            Always recommend consulting with a healthcare professional for serious concerns.
            Be empathetic, clear, and helpful in your responses.""",
                ),
                ("human", "{input}"),
            ]
        )

        # Create simple chain
        self.chain = self.medical_prompt | self.llm

        # Add callback handler for context management
        self.callback_handler = MedicalContextCallback(debugger, patient_id)

        # Initialize patient context
        self._initialize_patient_context()

    def _initialize_patient_context(self):
        """Initialize patient-specific context"""
        # Add patient profile context
        self.debugger.add_context(
            type=ContextType.ENVIRONMENT,
            key=f"patient_profile_{self.patient_id}",
            value=f"Patient ID: {self.patient_id}, Session started: {datetime.now().isoformat()}",
            priority=ContextPriority.HIGH,
            tags=["patient", "profile", "session"],
            agent_id=self.patient_id,
            metadata={
                "patient_id": self.patient_id,
                "session_start": datetime.now().isoformat(),
            },
        )

        # Add medical knowledge base context
        medical_knowledge = {
            "common_symptoms": ["fever", "headache", "cough", "fatigue", "nausea"],
            "emergency_symptoms": [
                "chest pain",
                "difficulty breathing",
                "severe bleeding",
                "loss of consciousness",
            ],
            "preventive_care": [
                "regular exercise",
                "balanced diet",
                "adequate sleep",
                "stress management",
            ],
        }

        self.debugger.add_context(
            type=ContextType.KNOWLEDGE,
            key=f"medical_knowledge_base_{self.patient_id}",
            value=json.dumps(medical_knowledge),
            priority=ContextPriority.CRITICAL,
            tags=["medical", "knowledge", "base"],
            agent_id=self.patient_id,
            metadata={"type": "knowledge_base", "scope": "medical"},
        )

    def chat(self, user_input: str) -> str:
        """Process user input and return medical response"""
        try:
            print(f"🏥 {self.patient_id}: {user_input}")

            # Add user input to conversation context
            self.debugger.add_context(
                type=ContextType.CONVERSATION,
                key=f"user_input_{int(time.time())}",
                value=user_input,
                priority=ContextPriority.MEDIUM,
                tags=["conversation", "user", "input"],
                agent_id=self.patient_id,
                metadata={"timestamp": datetime.now().isoformat()},
            )

            # Get medical response from Gemini
            response = self.chain.invoke({"input": user_input})

            # Store conversation history
            self.conversation_history.append(
                {"user": user_input, "assistant": response}
            )

            print(f"🤖 Medical Assistant: {response}")

            # Add medical response to context
            self.debugger.add_context(
                type=ContextType.KNOWLEDGE,
                key=f"medical_response_{int(time.time())}",
                value=response,
                priority=ContextPriority.HIGH,
                tags=["medical", "response", "advice"],
                agent_id=self.patient_id,
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "type": "medical_response",
                },
            )

            return response

        except Exception as e:
            error_msg = f"Error in medical consultation: {str(e)}"
            print(f"❌ {error_msg}")

            # Add error context
            self.debugger.add_context(
                type=ContextType.SYSTEM_STATE,
                key=f"medical_error_{int(time.time())}",
                value=error_msg,
                priority=ContextPriority.CRITICAL,
                tags=["error", "medical", "system"],
                agent_id=self.patient_id,
                metadata={
                    "error_type": "medical_consultation",
                    "timestamp": datetime.now().isoformat(),
                },
            )

            return "I apologize, but I'm experiencing technical difficulties. Please try again or consult with a healthcare professional."

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history from memory"""
        return self.conversation_history

    def add_medical_context(
        self, context_type: str, key: str, value: str, priority: str = "medium"
    ):
        """Add custom medical context"""
        priority_map = {
            "critical": ContextPriority.CRITICAL,
            "high": ContextPriority.HIGH,
            "medium": ContextPriority.MEDIUM,
            "low": ContextPriority.LOW,
        }

        self.debugger.add_context(
            type=ContextType.KNOWLEDGE,
            key=f"{context_type}_{key}_{int(time.time())}",
            value=value,
            priority=priority_map.get(priority, ContextPriority.MEDIUM),
            tags=["medical", context_type, "custom"],
            agent_id=self.patient_id,
            metadata={
                "context_type": context_type,
                "timestamp": datetime.now().isoformat(),
            },
        )


def create_medical_chatbots(
    debugger: WebPortalDebugger, gemini_api_key: str
) -> Dict[str, MedicalChatbot]:
    """Create multiple medical chatbots for demonstration"""
    patients = {
        "patient_001": "Alice Johnson",
        "patient_002": "Bob Smith",
        "patient_003": "Carol Davis",
    }

    chatbots = {}

    for patient_id, patient_name in patients.items():
        print(f"🏥 Creating medical chatbot for {patient_name} ({patient_id})")

        # Create and attach chatbot to debugger
        chatbot = MedicalChatbot(patient_id, debugger, gemini_api_key)
        chatbots[patient_id] = chatbot

        # Add patient information context
        debugger.add_context(
            type=ContextType.ENVIRONMENT,
            key=f"patient_info_{patient_id}",
            value=f"Patient: {patient_name}, ID: {patient_id}",
            priority=ContextPriority.HIGH,
            tags=["patient", "info", "medical"],
            agent_id=patient_id,
            metadata={"patient_name": patient_name, "patient_id": patient_id},
        )

    return chatbots


def simulate_medical_conversations(chatbots: Dict[str, MedicalChatbot]):
    """Simulate medical conversations for demonstration"""

    # Sample medical questions
    medical_questions = [
        "I've been having headaches for the past week. What could be causing this?",
        "What are the symptoms of a common cold?",
        "How can I improve my sleep quality?",
        "I feel tired all the time. What should I do?",
        "What are the benefits of regular exercise?",
        "I have a fever and body aches. Should I see a doctor?",
        "How can I manage stress better?",
        "What foods should I eat for better health?",
        "I'm having trouble breathing. Is this serious?",
        "What are the warning signs of a heart attack?",
    ]

    # Emergency scenarios
    emergency_questions = [
        "I have severe chest pain and can't breathe properly!",
        "I'm bleeding heavily from a cut!",
        "I think I'm having a heart attack!",
        "I can't move my arm and I'm dizzy!",
        "I have a severe allergic reaction!",
    ]

    while True:
        try:
            # Pick a random patient
            patient_id = random.choice(list(chatbots.keys()))
            chatbot = chatbots[patient_id]

            # 80% chance of regular question, 20% chance of emergency
            if random.random() < 0.8:
                question = random.choice(medical_questions)
            else:
                question = random.choice(emergency_questions)
                # Add emergency context
                chatbot.add_medical_context(
                    "emergency", "urgent_consultation", question, "critical"
                )

            # Process the question
            response = chatbot.chat(question)

            # Add conversation summary context
            chatbot.add_medical_context(
                "conversation_summary",
                f"session_{int(time.time())}",
                f"Q: {question[:50]}... A: {response[:50]}...",
                "medium",
            )

            # Wait between conversations
            time.sleep(random.uniform(15, 30))

        except Exception as e:
            print(f"❌ Error in medical conversation simulation: {e}")
            time.sleep(5)


def setup_medical_knowledge_base(debugger: WebPortalDebugger):
    """Set up medical knowledge base contexts"""
    print("📚 Setting up medical knowledge base...")

    # Medical conditions knowledge
    conditions = {
        "hypertension": "High blood pressure - monitor regularly, reduce sodium, exercise",
        "diabetes": "Blood sugar management - diet, exercise, medication compliance",
        "asthma": "Respiratory condition - avoid triggers, use inhalers as prescribed",
        "depression": "Mental health condition - therapy, medication, support systems",
    }

    for condition, info in conditions.items():
        debugger.add_context(
            type=ContextType.KNOWLEDGE,
            key=f"medical_condition_{condition}",
            value=info,
            priority=ContextPriority.HIGH,
            tags=["medical", "condition", "knowledge"],
            metadata={"condition": condition, "type": "medical_knowledge"},
        )

    # Medication information
    medications = {
        "aspirin": "Pain relief, anti-inflammatory - take with food, avoid alcohol",
        "ibuprofen": "NSAID pain reliever - can cause stomach issues, take with food",
        "acetaminophen": "Pain reliever - safe for most people, avoid alcohol",
        "metformin": "Diabetes medication - take with meals, monitor blood sugar",
    }

    for medication, info in medications.items():
        debugger.add_context(
            type=ContextType.KNOWLEDGE,
            key=f"medication_info_{medication}",
            value=info,
            priority=ContextPriority.CRITICAL,
            tags=["medical", "medication", "safety"],
            metadata={"medication": medication, "type": "medication_info"},
        )

    # Emergency protocols
    emergency_protocols = {
        "chest_pain": "Call 911 immediately, sit down, stay calm",
        "difficulty_breathing": "Call 911, use rescue inhaler if available",
        "severe_bleeding": "Apply direct pressure, elevate if possible, call 911",
        "loss_consciousness": "Call 911, check breathing, position safely",
    }

    for protocol, info in emergency_protocols.items():
        debugger.add_context(
            type=ContextType.SYSTEM_STATE,
            key=f"emergency_protocol_{protocol}",
            value=info,
            priority=ContextPriority.CRITICAL,
            tags=["emergency", "protocol", "medical"],
            metadata={"protocol": protocol, "type": "emergency_protocol"},
        )

    print("✅ Medical knowledge base setup complete")


def run_medical_chatbot_demo():
    """Run the complete medical chatbot demonstration"""
    print("🏥 Medical Chatbot Demo with AgentDebugger Context Management")
    print("=" * 70)

    # Check for Gemini API key
    gemini_api_key = "GEMINI API KEY"
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY environment variable not set!")
        print("Please set your Gemini API key:")
        print("export GEMINI_API_KEY='your_api_key_here'")
        print("Or add it to your .env file")
        return

    # Initialize web debugger
    from agent_debugger.web import init_web_debugger

    debugger_instance = init_web_debugger()
    if not debugger_instance:
        print("❌ Failed to initialize web debugger")
        return

    print("🧠 Setting up medical knowledge base...")
    setup_medical_knowledge_base(debugger_instance)

    print("🏥 Creating medical chatbots...")
    chatbots = create_medical_chatbots(debugger_instance, gemini_api_key)

    print(f"✅ Created {len(chatbots)} medical chatbots")

    # Start conversation simulation
    print("💬 Starting medical conversation simulation...")
    conversation_thread = threading.Thread(
        target=simulate_medical_conversations, args=(chatbots,), daemon=True
    )
    conversation_thread.start()

    print("\n📊 Web portal is running at: http://localhost:5000")
    print("🏥 Medical Chatbot Features:")
    print("  - Real-time medical conversations")
    print("  - Context management for patient data")
    print("  - Medical knowledge base")
    print("  - Emergency protocol tracking")
    print("  - Patient conversation history")
    print("  - Medical advice context storage")

    print("\n🧠 Navigate to the 'Context' tab to see:")
    print("  - Patient conversation contexts")
    print("  - Medical knowledge contexts")
    print("  - Emergency protocol contexts")
    print("  - Medication information contexts")
    print("  - Real-time context updates")

    print(f"\n🎉 Medical chatbot demo running with {len(chatbots)} patients!")
    print("💡 Open http://localhost:5000 in your browser")
    print("⏹️  Press Ctrl+C to stop the demo")

    return chatbots


if __name__ == "__main__":
    # Check dependencies
    try:
        import langchain
        import langchain_google_genai
    except ImportError:
        print("❌ Missing dependencies. Install with:")
        print("pip install langchain langchain-google-genai")
        exit(1)

    # Start the medical chatbot demo
    try:
        chatbots = run_medical_chatbot_demo()

        # Start the Flask server with SocketIO
        from agent_debugger.web import socketio, app

        print("🚀 Starting Flask server with medical chatbot demo...")
        socketio.run(app, debug=False, host="0.0.0.0", port=5000)

    except KeyboardInterrupt:
        print("\n👋 Medical chatbot demo stopped by user")
    except Exception as e:
        print(f"\n❌ Error running medical chatbot demo: {e}")
        import traceback

        traceback.print_exc()
