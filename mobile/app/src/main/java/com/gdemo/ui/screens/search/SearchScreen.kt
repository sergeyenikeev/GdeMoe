package com.gdemo.ui.screens.search

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.gdemo.data.local.loadConnection
import com.gdemo.data.model.Item
import com.gdemo.data.remote.ApiClient
import kotlinx.coroutines.launch

@Composable
fun SearchScreen(paddingValues: PaddingValues, onOpenItem: (String) -> Unit) {
    val context = LocalContext.current
    val stored = remember { context.loadConnection() }
    val baseUrl = remember { mutableStateOf(stored.baseUrl) }
    val query = remember { mutableStateOf("") }
    val status = remember { mutableStateOf("") }
    val results = remember { mutableStateOf<List<Item>>(emptyList()) }
    val message = remember { mutableStateOf("Введите запрос или статус и нажмите «Поиск»") }
    val scope = rememberCoroutineScope()
    val api = remember(baseUrl.value) { ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl.value)) }

    fun runSearch() {
        scope.launch {
            try {
                val items = api.searchItems(query.value, status.value.ifBlank { null })
                results.value = items
                message.value = if (items.isEmpty()) "Ничего не найдено" else "Найдено: ${items.size}"
            } catch (e: Exception) {
                message.value = "Ошибка: ${e.localizedMessage}"
            }
        }
    }

    Column(
        modifier = Modifier.padding(paddingValues).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        OutlinedTextField(
            value = query.value,
            onValueChange = { query.value = it },
            label = { Text("Текстовый поиск (название, описание)") },
            modifier = Modifier.fillMaxWidth()
        )
        OutlinedTextField(
            value = status.value,
            onValueChange = { status.value = it },
            label = { Text("Статус (ok/new/broken/needs_review, можно пусто)") },
            modifier = Modifier.fillMaxWidth()
        )
        Button(
            onClick = { runSearch() },
            modifier = Modifier.padding(top = 12.dp)
        ) {
            Text("Поиск")
        }
        Text(text = message.value)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(results.value) { item ->
                Card(
                    colors = CardDefaults.cardColors(),
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onOpenItem(item.id.toString()) }
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(item.title)
                        Text("Статус: ${item.status}")
                    }
                }
            }
        }
    }
}
