"""
Brain: Group Dynamics

Handles intelligent turn-taking in group chats where multiple human or AI users are present.
Uses a fast LLM call to determine if the bot should speak or remain silent based on context.
"""

from typing import List, Dict

class GroupDynamics:
    """Evaluates conversation context to decide if the bot should speak"""
    
    @staticmethod
    async def should_i_speak(llm, bot_name: str, chat_history: List[Dict], current_message: str) -> bool:
        """
        Evaluate if this specific bot should reply to the current message in a group chat.
        Returns True if the bot should speak, False if it should stay silent.
        """
        if not llm:
            # Fallback if no LLM: only respond if name is explicitly mentioned
            return bot_name.lower() in current_message.lower()
            
        # Format recent history for the prompt
        history_text = "\n".join([f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in chat_history[-5:]])
        if not history_text:
            history_text = "(No recent history)"

        prompt = f"""You are determining if an AI persona named {bot_name} should reply in a group chat.

Here is the recent chat history leading up to the current moment:
{history_text}

Here is the latest message that just arrived:
{current_message}

Based strictly on this context, is the user talking to {bot_name}? Is it {bot_name}'s turn to speak, or should they stay quiet and let someone else answer?
Consider whether {bot_name} was explicitly mentioned, asked a question, or if the flow of conversation naturally points to them.

Reply with EXACTLY ONE WORD: "YES" or "NO"."""

        try:
            # We use a very low limit to ensure a fast, single-word response
            response = await llm.chat([
                {"role": "system", "content": "You are a routing system. Output only YES or NO."},
                {"role": "user", "content": prompt}
            ], max_tokens=5, temperature=0.1)
            
            # Clean and evaluate the response
            clean_res = response.strip().upper()
            
            # Additional safety: if the name is explicitly in the message, heavily lean towards YES
            if bot_name.lower() in current_message.lower():
                print(f"[GroupDynamics] {bot_name} explicitly mentioned. Overriding LLM if needed.")
                return True
                
            will_speak = "YES" in clean_res
            print(f"[GroupDynamics] Should {bot_name} speak? {'YES' if will_speak else 'NO'} (LLM said: {clean_res})")
            return will_speak
            
        except Exception as e:
            print(f"[GroupDynamics] Error evaluating turn-taking: {e}")
            # Fallback
            return bot_name.lower() in current_message.lower()
