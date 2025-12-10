package com.gdemo.ui.screens.items

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gdemo.data.model.Item
import com.gdemo.data.remote.ApiClient
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class ItemViewModel : ViewModel() {
    private val _items = MutableStateFlow<List<Item>>(emptyList())
    val items: StateFlow<List<Item>> = _items

    fun load(baseUrl: String = "http://10.0.2.2:8000") {
        viewModelScope.launch {
            runCatching {
                ApiClient.create(baseUrl).items()
            }.onSuccess {
                _items.value = it
            }.onFailure {
                // при ошибке оставляем текущие данные
            }
        }
    }
}
