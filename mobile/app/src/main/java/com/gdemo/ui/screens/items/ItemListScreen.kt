package com.gdemo.ui.screens.items

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.Item
import com.gdemo.data.remote.ApiClient
import kotlinx.coroutines.launch

@Composable
fun ItemListScreen(paddingValues: PaddingValues, onItemClick: (Int) -> Unit) {
    val context = LocalContext.current
    val stored = remember { context.loadConnection() }
    var baseUrl by remember { mutableStateOf(stored.baseUrl) }
    var items by remember { mutableStateOf<List<Item>>(emptyList()) }
    var message by remember { mutableStateOf("Загружаем...") }
    val scope = rememberCoroutineScope()
    var api = remember(baseUrl) { ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl)) }

    fun refresh() {
        scope.launch {
            try {
                message = "Загружаем..."
                items = api.items()
                message = if (items.isEmpty()) "Пока нет карточек" else "Найдено: ${items.size}"
            } catch (e: Exception) {
                message = "Ошибка: ${e.localizedMessage}"
            }
        }
    }

    LaunchedEffect(baseUrl) { refresh() }

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (items.isEmpty()) {
            item { Text(text = message, modifier = Modifier.padding(12.dp)) }
        } else {
            items(items) { item ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onItemClick(item.id) }
                ) {
                    Text(
                        text = item.title,
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(12.dp)
                    )
                    Text(
                        text = "Статус: ${item.status} • ${item.location ?: "без места"}",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
                    )
                    if (item.needsReview) {
                        Text(
                            text = "Нужно проверить",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.error,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
                        )
                    }
                }
            }
        }
    }
}
