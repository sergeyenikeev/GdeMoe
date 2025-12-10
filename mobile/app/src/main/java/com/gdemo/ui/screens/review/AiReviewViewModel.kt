package com.gdemo.ui.screens.review

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gdemo.data.model.AiDetectionDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.repository.AiRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class AiReviewUiState(
    val items: List<AiDetectionDto> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

class AiReviewViewModel(
    baseUrl: String
) : ViewModel() {
    private val api = ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl))
    private val repo = AiRepository(api)
    private val _ui = MutableStateFlow(AiReviewUiState(isLoading = true))
    val ui: StateFlow<AiReviewUiState> = _ui

    init {
        refresh()
    }

    fun refresh() = viewModelScope.launch {
        runCatching {
            _ui.value = _ui.value.copy(isLoading = true, error = null)
            val data = repo.pending()
            _ui.value = AiReviewUiState(items = data, isLoading = false)
        }.onFailure { err ->
            _ui.value = _ui.value.copy(isLoading = false, error = err.localizedMessage)
        }
    }

    fun accept(id: Int) = viewModelScope.launch {
        runCatching { repo.accept(id) }
        refresh()
    }

    fun reject(id: Int) = viewModelScope.launch {
        runCatching { repo.reject(id) }
        refresh()
    }
}
