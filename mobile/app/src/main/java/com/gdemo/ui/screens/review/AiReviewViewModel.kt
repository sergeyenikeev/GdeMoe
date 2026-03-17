package com.gdemo.ui.screens.review

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gdemo.data.model.AiDetectionDto
import com.gdemo.data.model.UploadHistoryEntryDto
import com.gdemo.data.remote.ApiClient
import com.gdemo.data.repository.AiRepository
import com.gdemo.util.AnalyticsLogger
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class AiReviewUiState(
    val items: List<AiDetectionDto> = emptyList(),
    val history: List<UploadHistoryEntryDto> = emptyList(),
    val isLoading: Boolean = false,
    val isHistoryLoading: Boolean = false,
    val error: String? = null
)

/**
 * ViewModel экрана AI Review.
 *
 * Держит две связанные ленты:
 * - очередь необработанных детекций;
 * - историю загрузок и уже принятых решений.
 */
class AiReviewViewModel(
    baseUrl: String
) : ViewModel() {
    private val api = ApiClient.create(ApiClient.sanitizeBaseUrl(baseUrl))
    private val repo = AiRepository(api)
    private val _ui = MutableStateFlow(AiReviewUiState(isLoading = true, isHistoryLoading = true))
    val ui: StateFlow<AiReviewUiState> = _ui

    init {
        refresh()
        refreshHistory()
    }

    fun refresh() = viewModelScope.launch {
        // Очередь и история грузятся отдельно, чтобы экран мог показать хотя бы
        // одну из секций, даже если вторая временно не ответила.
        runCatching {
            _ui.value = _ui.value.copy(isLoading = true, error = null)
            val data = repo.pending()
            _ui.value = _ui.value.copy(items = data, isLoading = false)
        }.onFailure { err ->
            _ui.value = _ui.value.copy(isLoading = false, error = err.localizedMessage)
        }
    }

    fun refreshHistory() = viewModelScope.launch {
        runCatching {
            _ui.value = _ui.value.copy(isHistoryLoading = true, error = null)
            val historyItems = repo.history()
            _ui.value = _ui.value.copy(history = historyItems, isHistoryLoading = false)
        }.onFailure { err ->
            _ui.value = _ui.value.copy(isHistoryLoading = false, error = err.localizedMessage)
        }
    }

    fun accept(id: Int) = viewModelScope.launch {
        _ui.value = _ui.value.copy(error = null)
        runCatching {
            repo.accept(id)
            repo.log(id, action = "accept")
            AnalyticsLogger.event("ai_accept", mapOf("detectionId" to id))
        }.onFailure { err ->
            _ui.value = _ui.value.copy(error = err.localizedMessage)
        }
        // После действия обновляем обе вкладки: запись уходит из Queue и появляется в History.
        refresh()
        refreshHistory()
    }

    fun reject(id: Int) = viewModelScope.launch {
        _ui.value = _ui.value.copy(error = null)
        runCatching {
            repo.reject(id)
            repo.log(id, action = "reject")
            AnalyticsLogger.event("ai_reject", mapOf("detectionId" to id))
        }.onFailure { err ->
            _ui.value = _ui.value.copy(error = err.localizedMessage)
        }
        refresh()
        refreshHistory()
    }

    fun updateObject(objectId: Int, itemId: Int?, locationId: Int?, decision: String? = null) = viewModelScope.launch {
        AnalyticsLogger.event("ai_object_update", mapOf("objectId" to objectId, "itemId" to itemId, "locationId" to locationId))
        runCatching { repo.updateObject(objectId, itemId, locationId, decision) }
            .onFailure { _ui.value = _ui.value.copy(error = it.localizedMessage) }
        // Редактирование объекта меняет summary и может повлиять на историю.
        refresh()
        refreshHistory()
    }
}
