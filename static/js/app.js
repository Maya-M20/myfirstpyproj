async function testAPI() {
    const responseDiv = document.getElementById('response');
    responseDiv.innerHTML = '⌛ Тестируем API...';
    
    try {
        // 1. Тест главной страницы
        const homeResponse = await fetch('/');
        const homeText = await homeResponse.text();
        
        // 2. Тест API с обработкой HTML/JSON
        const apiResponse = await fetch('/molecules');
        const contentType = apiResponse.headers.get('content-type');
        
        let apiData;
        if (contentType && contentType.includes('application/json')) {
            apiData = await apiResponse.json();
        } else {
            const text = await apiResponse.text();
            throw new Error(`Получен HTML вместо JSON: ${text.substring(0, 100)}...`);
        }
        
        // 3. Тест Redis
        const redisResponse = await fetch('/cache/stats');
        const redisData = await redisResponse.json();
        
        responseDiv.innerHTML = `
            <h3>✅ API работает!</h3>
            <p><strong>Главная страница:</strong> ${homeResponse.status}</p>
            <p><strong>Молекул в БД:</strong> ${apiData.total || 0}</p>
            <p><strong>Redis:</strong> ${redisData.redis || 'не доступен'}</p>
            <pre>${JSON.stringify(redisData, null, 2)}</pre>
        `;
    } catch (error) {
        responseDiv.innerHTML = `
            <h3>❌ Ошибка API</h3>
            <p><strong>Сообщение:</strong> ${error.message}</p>
            <p><strong>Проверьте:</strong></p>
            <ol>
                <li>Контейнер API запущен: <code>docker ps | grep api</code></li>
                <li>Nginx конфиг правильный</li>
                <li>API доступно на порту 8080</li>
            </ol>
        `;
    }
}