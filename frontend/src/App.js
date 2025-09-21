import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  Github, 
  Loader2, 
  CheckCircle, 
  AlertCircle, 
  MessageSquare, 
  Sparkles, 
  Code, 
  FileText, 
  Zap, 
  Brain, 
  ArrowRight, 
  Bot,
  User,
  Trash2,
  Star,
  GitBranch,
  Clock
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState(null);
  const [question, setQuestion] = useState('');
  const [sources, setSources] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [conversationHistory, setConversationHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isQuerying, setIsQuerying] = useState(false);
  const [loading, setLoading] = useState(false);        // tracks query in progress
  const [responses, setResponses] = useState([]);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const [replacingMessage, setReplacingMessage] = useState(false);

  // ---- Poll for backend progress ----
  useEffect(() => {
    if (sessionId && status?.status === 'indexing') {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/status/${sessionId}`);
          setStatus(response.data);
        } catch (error) {
          console.error('Error fetching status:', error);
        }
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [sessionId, status?.status]);

  // ---- Auto-scroll to bottom when new messages arrive ----
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversationHistory, isQuerying]);

  // ---- Auto-resize textarea ----
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [question]);

  // ---- Handle keyboard shortcuts ----
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (question.trim() && !isQuerying) {
        handleQuery(e);
      }
    }
  };

  const handleIndexRepo = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    setIsLoading(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/index`, {
        repo_url: repoUrl.trim()
      });

      setSessionId(response.data.session_id);
      setStatus({
        status: 'indexing',
        message: 'Cloning repository...',
        progress: 0
      });
      setSources([]);
      setConversationId(null);
      setConversationHistory([]);
    } catch (error) {
      console.error('Error indexing repository:', error);
      alert('Error indexing repository. Please check the URL and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  async function handleQuery(e) {
    e.preventDefault(); // Prevent form submission reload

    if (!question || question.trim() === "") {
        console.warn("Cannot send empty question");
        return;
    }

    if (!status || status.status !== "ready") {
        console.warn(`Repo not ready. Current status: ${status?.status}`);
        return;
    }

    const userMessage = question.trim();
    setQuestion(""); // Clear input immediately

    try {
        // Add user message immediately
        setConversationHistory(prev => [...prev, {
            role: 'user',
            content: userMessage,
            id: Date.now() // Add unique ID for smooth transitions
        }]);

        setIsQuerying(true);

        const response = await axios.post(`${API_BASE_URL}/query`, {
            session_id: sessionId,
            question: userMessage,
            conversation_history: conversationHistory
        });

        // Add assistant message with smooth transition
        setTimeout(() => {
            setReplacingMessage(true);
            
            setConversationHistory(prev => {
                const newHistory = [...prev];
                // Remove any existing "thinking" message and add the real response
                const filteredHistory = newHistory.filter(msg => msg.role !== 'thinking');
                return [...filteredHistory, {
                    role: 'assistant',
                    content: response.data.answer,
                    confidence: response.data.confidence || 'medium',
                    id: Date.now() + 1,
                    isNew: true // Mark as new for animation
                }];
            });

            // Update sources if available
            if (response.data.sources) {
                setSources(response.data.sources);
            }
            
            // Reset replacing state after animation
            setTimeout(() => setReplacingMessage(false), 300);
        }, 500); // Small delay for smooth transition

    } catch (err) {
        console.error("Error querying repository:", err);
        
        // Add error message with smooth transition
        setTimeout(() => {
            setReplacingMessage(true);
            
            setConversationHistory(prev => {
                const newHistory = [...prev];
                const filteredHistory = newHistory.filter(msg => msg.role !== 'thinking');
                return [...filteredHistory, {
                    role: 'assistant',
                    content: "Sorry, I encountered an error while processing your request. Please try again.",
                    confidence: 'low',
                    id: Date.now() + 1,
                    isError: true,
                    isNew: true
                }];
            });
            
            // Reset replacing state after animation
            setTimeout(() => setReplacingMessage(false), 300);
        }, 500);
    } finally {
        setIsQuerying(false);
    }
}


  

  // ---- UI helpers ----
  const getStatusIcon = () => {
    if (!status) return null;

    switch (status.status) {
      case 'indexing':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
      case 'ready':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusColor = () => {
    if (!status) return 'text-gray-500';

    switch (status.status) {
      case 'indexing':
        return 'text-blue-500';
      case 'ready':
        return 'text-green-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'high':
        return 'text-white bg-green-600 border-green-600';
      case 'medium':
        return 'text-white bg-yellow-500 border-yellow-500';
      case 'low':
        return 'text-white bg-red-600 border-red-600';
      default:
        return 'text-gray-600 bg-gray-200 border-gray-300';
    }
  };

  const clearConversation = () => {
    setConversationHistory([]);
    setSources([]);
    if (conversationId) {
      axios.delete(`${API_BASE_URL}/conversation/${conversationId}`)
        .catch(error => console.error('Error clearing conversation:', error));
    }
  };

  // Latest assistant reply
  const latestAssistantMsg = [...conversationHistory].reverse().find(msg => msg.role === 'assistant');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md shadow-lg border-b border-white/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl blur-sm opacity-75"></div>
                <div className="relative bg-gradient-to-r from-blue-600 to-purple-600 p-2 rounded-xl">
                  <Github className="w-8 h-8 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 bg-clip-text text-transparent">
                  GitSleuth
                </h1>
                <p className="text-sm text-gray-600 flex items-center space-x-1">
                  <Sparkles className="w-4 h-4" />
                  <span>AI-powered code intelligence</span>
                </p>
              </div>
            </div>
            <div className="hidden md:flex items-center space-x-6">
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <Brain className="w-4 h-4" />
                <span>Smart Analysis</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <Zap className="w-4 h-4" />
                <span>Lightning Fast</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero Section */}
        {!sessionId && (
          <div className="text-center mb-12">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full mb-6">
              <Code className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Analyze Any GitHub Repository
            </h2>
            <p className="text-xl text-gray-600 max-w-2xl mx-auto">
              Upload a repository and ask intelligent questions about its codebase. 
              Get instant insights powered by AI.
            </p>
          </div>
        )}

        {/* Repository Input Section */}
        <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-8 mb-8 animate-fadeInUp">
          <div className="flex items-center space-x-3 mb-6">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg">
              <GitBranch className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900">Index Repository</h2>
          </div>
          
          <form onSubmit={handleIndexRepo} className="space-y-6">
            <div>
              <label htmlFor="repoUrl" className="block text-sm font-semibold text-gray-700 mb-3">
                GitHub Repository URL
              </label>
              <div className="flex space-x-4">
                <div className="flex-1 relative">
                  <input
                    type="url"
                    id="repoUrl"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-lg"
                    required
                  />
                  <Github className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                </div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl hover:from-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-all duration-200 shadow-lg hover:shadow-xl btn-hover"
                >
                  {isLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Search className="w-5 h-5" />
                  )}
                  <span className="font-semibold">{isLoading ? 'Indexing...' : 'Analyze'}</span>
                </button>
              </div>
            </div>
          </form>

          {/* Status Display */}
          {status && (
            <div className="mt-6 p-6 bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl border border-blue-200">
              <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                  {getStatusIcon()}
                </div>
                <div className="flex-1">
                  <p className={`text-lg font-semibold ${getStatusColor()}`}>
                    {status.message}
                  </p>
                  {status.progress !== undefined && (
                    <div className="mt-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-gray-700">Progress</span>
                        <span className="text-sm font-bold text-blue-600">{status.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                        <div 
                          className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500 ease-out shadow-sm"
                          style={{ width: `${status.progress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ChatGPT-style Chat Interface */}
        {status?.status === 'ready' && (
          <div className="flex flex-col h-[calc(100vh-200px)] bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 animate-fadeInUp">
            {/* Chat Header */}
            <div className="flex justify-between items-center p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50 rounded-t-2xl">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-gradient-to-r from-green-500 to-blue-500 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">AI Code Assistant</h2>
                  <p className="text-sm text-gray-600">Ask questions about your codebase</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                {conversationHistory.length > 0 && (
                  <button
                    onClick={clearConversation}
                    className="px-4 py-2 text-sm text-red-600 hover:text-red-800 border border-red-300 rounded-lg hover:bg-red-50 transition-all duration-200 flex items-center space-x-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span>Clear Chat</span>
                  </button>
                )}
                <div className="flex items-center space-x-2 text-sm text-gray-600">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span>Online</span>
                </div>
              </div>
            </div>

            {/* Chat Messages Area */}
            <div className="flex-1 overflow-y-auto chat-scroll p-6 space-y-6">
              {conversationHistory.length === 0 ? (
                /* Welcome Message */
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center mb-6">
                    <Bot className="w-10 h-10 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-4">Welcome to GitSleuth AI</h3>
                  <p className="text-gray-600 mb-8 max-w-md">
                    I'm your AI code assistant. Ask me anything about the codebase you've indexed. 
                    I can help you understand functions, find files, explain architecture, and more!
                  </p>
                  
                  {/* Quick Question Suggestions */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
                    {[
                      "How does authentication work?",
                      "What are the main API endpoints?",
                      "Where is the database configuration?",
                      "How is error handling implemented?"
                    ].map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => setQuestion(suggestion)}
                        className="p-4 text-left bg-white border border-gray-200 rounded-xl hover:bg-blue-50 hover:border-blue-300 transition-all duration-200 text-gray-700 hover:text-blue-700 shadow-sm hover:shadow-md suggestion-card"
                      >
                        <div className="flex items-center space-x-3">
                          <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                            <MessageSquare className="w-4 h-4 text-white" />
                          </div>
                          <span className="font-medium">{suggestion}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Chat Messages */
                <>
                  {conversationHistory.map((message, index) => {
                    const isAssistant = message.role === 'assistant';
                    const isUser = message.role === 'user';
                    const isLastMessage = index === conversationHistory.length - 1;
                    const isError = message.isError;
                    const isNewMessage = message.isNew;
                    
                    return (
                      <div
                        key={message.id || index}
                        className={`flex ${isAssistant ? 'justify-start' : 'justify-end'} ${
                          isNewMessage ? 'message-bubble-entrance' : 'message-enter message-enter-active'
                        } ${replacingMessage && isNewMessage ? 'message-replace-entering' : ''}`}
                        style={{ 
                          animationDelay: isNewMessage ? '0s' : `${index * 0.1}s`,
                          transition: 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)'
                        }}
                      >
                        <div className={`flex space-x-3 max-w-[80%] ${isAssistant ? 'flex-row' : 'flex-row-reverse'}`}>
                          {/* Avatar */}
                          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-lg transition-all duration-300 hover:scale-110 ${
                            isAssistant 
                              ? isError 
                                ? 'bg-gradient-to-r from-red-500 to-red-600'
                                : 'bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500'
                              : 'bg-gradient-to-r from-gray-600 to-gray-700'
                          }`}>
                            {isAssistant ? (
                              <Bot className="w-5 h-5 text-white" />
                            ) : (
                              <User className="w-5 h-5 text-white" />
                            )}
                          </div>
                          
                          {/* Message Bubble */}
                          <div className={`flex-1 ${isAssistant ? 'text-left' : 'text-right'}`}>
                            <div className={`inline-block p-4 message-bubble transition-all duration-500 hover:shadow-xl ${
                              isAssistant 
                                ? isError
                                  ? 'assistant-message border-red-200 bg-red-50'
                                  : 'assistant-message hover:border-blue-300'
                                : 'user-message hover:from-blue-600 hover:to-purple-600'
                            } ${isLastMessage ? 'ring-2 ring-blue-200' : ''}`}>
                              <p className={`whitespace-pre-wrap leading-relaxed ${
                                isAssistant 
                                  ? isError 
                                    ? 'text-red-800' 
                                    : 'text-gray-800' 
                                  : 'text-white'
                              }`}>
                                {message.content}
                              </p>
                            </div>
                            
                            {/* Confidence Badge for Assistant */}
                            {isAssistant && !isError && (
                              <div className="mt-3 flex items-center space-x-2">
                                <span className={`px-3 py-1 text-xs rounded-full font-medium shadow-sm confidence-badge ${getConfidenceColor(message.confidence)}`}>
                                  <Star className="w-3 h-3 inline mr-1" />
                                  {message.confidence || 'medium'} confidence
                                </span>
                                <span className="text-xs text-gray-500">
                                  {new Date().toLocaleTimeString()}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  
                  {/* Typing Indicator */}
                  {isQuerying && (
                    <div className="flex justify-start animate-fadeInUp">
                      <div className="flex space-x-3">
                        <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center shadow-lg bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500 animate-pulse">
                          <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1">
                          <div className="inline-block p-4 rounded-2xl shadow-lg bg-white border border-gray-200 animate-pulse">
                            <div className="typing-indicator">
                              <div className="typing-dot"></div>
                              <div className="typing-dot"></div>
                              <div className="typing-dot"></div>
                              <span className="ml-3 text-gray-600 text-sm">GitSleuth is thinking...</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Scroll to bottom anchor */}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Fixed Input Area at Bottom */}
            <div className="p-6 border-t border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50 rounded-b-2xl">
              <form onSubmit={handleQuery} className="space-y-4">
                <div className="relative bg-white rounded-2xl border border-gray-200 shadow-lg input-focus-ring transition-all duration-200">
                  <div className="flex items-end space-x-3 p-4">
                    <div className="flex-1">
                      <textarea
                        ref={textareaRef}
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask me anything about the codebase... (Press Enter to send, Shift+Enter for new line)"
                        className="w-full auto-resize-textarea border-0 outline-none text-lg placeholder-gray-400 bg-transparent"
                        rows="1"
                        required
                      />
                    </div>
                    
                    <button
                      type="submit"
                      disabled={isQuerying || !question.trim()}
                      className="flex-shrink-0 p-3 bg-gradient-to-r from-green-600 via-blue-600 to-purple-600 text-white rounded-xl hover:from-green-700 hover:via-blue-700 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg hover:shadow-xl transform hover:scale-105 disabled:transform-none"
                    >
                      {isQuerying ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                      ) : (
                        <ArrowRight className="w-5 h-5" />
                      )}
                    </button>
                  </div>
                  
                  {/* Character count and suggestions */}
                  <div className="px-4 pb-3 flex justify-between items-center text-sm text-gray-500">
                    <div className="flex items-center space-x-4">
                      {question.length > 0 && (
                        <span className="bg-gray-100 px-2 py-1 rounded-full">
                          {question.length} characters
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      <Sparkles className="w-4 h-4 text-blue-400" />
                      <span>Powered by GPT-4</span>
                    </div>
                  </div>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
