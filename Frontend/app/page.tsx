'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'

interface Channel {
  id: string
  name: string
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

export default function Home() {
  const [isDarkTheme, setIsDarkTheme] = useState(false)
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null)
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [resultText, setResultText] = useState('')
  const [showResult, setShowResult] = useState(false)
  const [showChannels, setShowChannels] = useState(false)
  const [availableChannels, setAvailableChannels] = useState<Channel[]>([])
  const [selectedChannels, setSelectedChannels] = useState<string[]>([])
  const [currentArticleText, setCurrentArticleText] = useState('')

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light'
    if (savedTheme === 'dark') {
      setIsDarkTheme(true)
      document.body.classList.add('dark-theme')
    }
    loadChannels()
  }, [])

  const toggleTheme = () => {
    const newTheme = !isDarkTheme
    setIsDarkTheme(newTheme)
    if (newTheme) {
      document.body.classList.add('dark-theme')
      localStorage.setItem('theme', 'dark')
    } else {
      document.body.classList.remove('dark-theme')
      localStorage.setItem('theme', 'light')
    }
  }

  const loadChannels = async () => {
    try {
      const response = await fetch(`${API_URL}/api/channels`)
      const data = await response.json()
      if (data.success) {
        setAvailableChannels(data.channels)
      }
    } catch (error) {
      console.error('Ошибка загрузки каналов:', error)
    }
  }

  const handleStyleSelect = (style: string) => {
    setSelectedStyle(style)
  }

  const handleSubmit = () => {
    if (!url.trim()) {
      alert('Пожалуйста, введите URL статьи')
      return
    }

    if (!selectedStyle) {
      alert('Пожалуйста, выберите стиль рерайта')
      return
    }

    setLoading(true)
    setShowResult(false)

    setTimeout(() => {
      const processedArticle = `Статья успешно обработана!\n\nURL: ${url}\nСтиль: ${getStyleName(selectedStyle)}\n\n[Здесь будет результат рерайта статьи]`
      setCurrentArticleText(processedArticle)
      setResultText(processedArticle)
      setShowResult(true)
      setShowChannels(false)
      setLoading(false)
    }, 2000)
  }

  const handleSocialClick = (social: string) => {
    if (social === 'telegram') {
      if (!currentArticleText) {
        alert('Сначала обработайте статью')
        return
      }
      if (availableChannels.length === 0) {
        alert('Каналы не настроены. Используйте бота для добавления каналов.')
        return
      }
      setShowChannels(true)
    } else {
      alert(`Публикация в ${social === 'vk' ? 'Вконтакте' : 'Instagram'}`)
    }
  }

  const handleChannelToggle = (channelId: string) => {
    setSelectedChannels(prev =>
      prev.includes(channelId)
        ? prev.filter(id => id !== channelId)
        : [...prev, channelId]
    )
  }

  const handleSendTelegram = async () => {
    if (selectedChannels.length === 0) {
      alert('Выберите хотя бы один канал')
      return
    }

    try {
      const response = await fetch(`${API_URL}/api/send-article`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          article_text: currentArticleText,
          channels: selectedChannels
        })
      })

      const data = await response.json()

      if (data.success) {
        alert(`Статья отправлена в ${data.sent} из ${data.total} каналов`)
        setShowChannels(false)
        setSelectedChannels([])
      } else {
        alert(`Ошибка: ${data.error}`)
      }
    } catch (error) {
      console.error('Ошибка отправки:', error)
      alert('Ошибка отправки статьи')
    }
  }

  const getStyleName = (style: string) => {
    const styles: Record<string, string> = {
      'scientific': 'Научно-деловой стиль',
      'meme': 'Мемный стиль',
      'casual': 'Повседневный стиль'
    }
    return styles[style] || style
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSubmit()
    }
  }

  return (
    <div className="container">
      <div className="header">
        <button className="theme-toggle" onClick={toggleTheme}>
          {isDarkTheme ? '☀️ Светлая' : '🌙 Тёмная'}
        </button>
        <Image
          src="/logo.png"
          alt="Phoenix Lab Logo"
          width={120}
          height={120}
          className="logo"
          priority
        />
        <h1>Phoenix Lab</h1>
        <p className="subtitle">AI Рерайт Статей</p>
      </div>

      <div className="main-content">
        <div className="input-section">
          <label htmlFor="article-url">URL статьи</label>
          <input
            type="url"
            id="article-url"
            className="url-input"
            placeholder="https://example.com/article"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyPress={handleKeyPress}
          />
        </div>

        <div className="style-section">
          <label>Стиль рерайта</label>
          <div className="style-buttons">
            <button
              className={`style-btn ${selectedStyle === 'scientific' ? 'active' : ''}`}
              onClick={() => handleStyleSelect('scientific')}
            >
              Научно-деловой стиль
            </button>
            <button
              className={`style-btn ${selectedStyle === 'meme' ? 'active' : ''}`}
              onClick={() => handleStyleSelect('meme')}
            >
              Мемный стиль
            </button>
            <button
              className={`style-btn ${selectedStyle === 'casual' ? 'active' : ''}`}
              onClick={() => handleStyleSelect('casual')}
            >
              Повседневный стиль
            </button>
          </div>
        </div>

        <div className="social-section">
          <label>Публикация в соцсетях</label>
          <div className="social-buttons">
            <button className="social-btn" onClick={() => handleSocialClick('vk')}>
              Вконтакте
            </button>
            <button className="social-btn" onClick={() => handleSocialClick('telegram')}>
              Telegram
            </button>
            <button className="social-btn" onClick={() => handleSocialClick('instagram')}>
              Instagram
            </button>
          </div>
        </div>

        <button className="submit-btn" onClick={handleSubmit} disabled={loading}>
          Рерайт статьи
        </button>

        <div className={`loading ${loading ? 'show' : ''}`}>
          <div className="spinner"></div>
          <p>Обработка статьи...</p>
        </div>

        <div className={`result-section ${showResult ? 'show' : ''}`}>
          <div className="result-box">
            <div className="result-title">Результат рерайта:</div>
            <div className="result-text">{resultText}</div>
            {showChannels && (
              <div className="channels-selection">
                <label style={{ display: 'block', marginBottom: '10px', color: '#ffffff' }}>
                  Выберите каналы для отправки:
                </label>
                <div className="channels-list">
                  {availableChannels.map((channel) => (
                    <label key={channel.id}>
                      <input
                        type="checkbox"
                        checked={selectedChannels.includes(channel.id)}
                        onChange={() => handleChannelToggle(channel.id)}
                      />
                      {channel.name || channel.id}
                    </label>
                  ))}
                </div>
                <button className="submit-btn" onClick={handleSendTelegram} style={{ marginTop: '10px' }}>
                  Отправить в Telegram
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

