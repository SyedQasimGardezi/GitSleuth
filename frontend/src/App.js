import React, { useState, useEffect } from 'react';
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

  const handleQuery = async (e) => {
    e.preventDefault();
    if (!question.trim() || !sessionId) return;

    setIsQuerying(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/query`, {
        session_id: sessionId,
        question: question.trim(),
        conversation_history: conversationHistory
      });

      setSources(response.data.sources || []);
      setConversationId(response.data.conversation_id);

      const newHistory = [
        ...conversationHistory,
        { role: 'user', content: question.trim(), confidence: '' },
        {
          role: 'assistant',
          content: response.data.answer,
          confidence: response.data.confidence // use backend confidence
        }
      ];
      setConversationHistory(newHistory);
      setQuestion('');
    } catch (error) {
      console.error('Error querying repository:', error);
      alert('Error querying repository. Please try again.');
    } finally {
      setIsQuerying(false);
    }
  };

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

        {/* Query Section */}
        {status?.status === 'ready' && (
          <div className="bg-white/70 backdrop-blur-sm rounded-2xl shadow-xl border border-white/20 p-8 animate-fadeInUp">
            <div className="flex justify-between items-center mb-8">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-gradient-to-r from-green-500 to-blue-500 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-white" />
                </div>
                <h2 className="text-2xl font-bold text-gray-900">Ask Questions</h2>
              </div>
              {conversationHistory.length > 0 && (
                <button
                  onClick={clearConversation}
                  className="px-4 py-2 text-sm text-red-600 hover:text-red-800 border border-red-300 rounded-lg hover:bg-red-50 transition-all duration-200 flex items-center space-x-2"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Clear Chat</span>
                </button>
              )}
            </div>
            
            {/* Query Form */}
            <form onSubmit={handleQuery} className="space-y-6">
              <div>
                <label htmlFor="question" className="block text-sm font-semibold text-gray-700 mb-3">
                  Ask a question about the codebase
                </label>
                <div className="flex space-x-4">
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      id="question"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      placeholder="e.g., Where is authentication logic handled? How does the API work?"
                      className="w-full px-4 py-3 border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 text-lg"
                      required
                    />
                    <Bot className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                  </div>
                  <button
                    type="submit"
                    disabled={isQuerying}
                    className="px-8 py-3 bg-gradient-to-r from-green-600 to-blue-600 text-white rounded-xl hover:from-green-700 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-all duration-200 shadow-lg hover:shadow-xl btn-hover"
                  >
                    {isQuerying ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <ArrowRight className="w-5 h-5" />
                    )}
                    <span className="font-semibold">{isQuerying ? 'Thinking...' : 'Ask'}</span>
                  </button>
                </div>
              </div>
            </form>

            {/* Conversation History */}
            {conversationHistory.length > 0 && (
              <div className="mt-8">
                <div className="flex items-center space-x-2 mb-6">
                  <Clock className="w-5 h-5 text-gray-500" />
                  <h3 className="text-lg font-semibold text-gray-900">Conversation</h3>
                </div>
                <div className="space-y-6 max-h-96 overflow-y-auto pr-2">
                  {conversationHistory.map((message, index) => {
                    const isAssistant = message.role === 'assistant';
                    return (
                      <div
                        key={index}
                        className={`flex space-x-4 ${isAssistant ? 'justify-start' : 'justify-end'}`}
                      >
                        <div className={`flex space-x-3 max-w-3xl ${isAssistant ? 'flex-row' : 'flex-row-reverse'}`}>
                          {/* Avatar */}
                          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                            isAssistant 
                              ? 'bg-gradient-to-r from-blue-500 to-purple-500' 
                              : 'bg-gradient-to-r from-gray-500 to-gray-600'
                          }`}>
                            {isAssistant ? (
                              <Bot className="w-4 h-4 text-white" />
                            ) : (
                              <User className="w-4 h-4 text-white" />
                            )}
                          </div>
                          
                          {/* Message */}
                          <div className={`flex-1 ${isAssistant ? 'text-left' : 'text-right'}`}>
                            <div className={`inline-block p-4 rounded-2xl ${
                              isAssistant 
                                ? 'bg-white border border-gray-200 shadow-sm' 
                                : 'bg-gradient-to-r from-blue-500 to-purple-500 text-white'
                            }`}>
                              <p className={`whitespace-pre-wrap ${
                                isAssistant ? 'text-gray-800' : 'text-white'
                              }`}>
                                {message.content}
                              </p>
                            </div>
                            
                            {/* Confidence Badge for Assistant */}
                            {isAssistant && (
                              <div className="mt-2 flex items-center space-x-2">
                                <span className={`px-3 py-1 text-xs rounded-full font-medium ${getConfidenceColor(message.confidence)}`}>
                                  {message.confidence || 'medium'} confidence
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Latest Answer - Only show if no conversation history */}
            {latestAssistantMsg && conversationHistory.length === 0 && (
              <div className="mt-8">
                <div className="flex items-center space-x-3 mb-6">
                  <div className="p-2 bg-gradient-to-r from-green-500 to-blue-500 rounded-lg">
                    <Star className="w-5 h-5 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">Latest Answer</h3>
                  <span className={`px-3 py-1 text-sm rounded-full font-medium ${getConfidenceColor(latestAssistantMsg.confidence)}`}>
                    {latestAssistantMsg.confidence || 'medium'} confidence
                  </span>
                </div>
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-200">
                  <p className="text-gray-800 whitespace-pre-wrap text-lg leading-relaxed">{latestAssistantMsg.content}</p>
                </div>

                {/* Sources */}
                {sources.length > 0 && (
                  <div className="mt-6">
                    <div className="flex items-center space-x-2 mb-4">
                      <FileText className="w-5 h-5 text-gray-600" />
                      <h4 className="text-lg font-semibold text-gray-900">Sources</h4>
                    </div>
                    <div className="grid gap-4 md:grid-cols-2">
                      {sources.map((source, index) => (
                        <div key={index} className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow duration-200">
                          <div className="flex items-start space-x-3">
                            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                              <Code className="w-4 h-4 text-white" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-semibold text-blue-600 mb-2 truncate">
                                {source.file}
                                {source.line_number && (
                                  <span className="text-gray-500 font-normal"> (line {source.line_number})</span>
                                )}
                              </p>
                              <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded-lg font-mono text-xs leading-relaxed">
                                {source.snippet}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
