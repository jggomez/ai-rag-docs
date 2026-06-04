/**
 * SubmitQuery Use Case
 *
 * Sends a user question to the ADK agent and returns the response text.
 * The caller must supply a sessionId that identifies the current conversation.
 * A new sessionId should be generated for each fresh chat session so the
 * agent starts with a clean conversation history.
 */
import { queryAgent } from '../infrastructure/api/ApiRepository.js';

/**
 * Execute a query against the RAG agent.
 * @param {string} userMessage - The user's question text.
 * @param {string} sessionId   - Unique session ID for this conversation (UUID).
 * @returns {Promise<string>} The agent's response text.
 */
export async function executeSubmitQuery(userMessage, sessionId) {
  return queryAgent(userMessage, sessionId);
}
