package com.gdemo.util

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlin.random.Random

class UploadQueue(
    private val scope: CoroutineScope,
    private val maxRetries: Int = 3,
    private val baseDelayMs: Long = 1500L
) {
    enum class Status { PENDING, RUNNING, RETRYING, SUCCESS, FAILED }

    data class TaskState(
        val id: Long,
        val label: String,
        val attempts: Int = 0,
        val status: Status = Status.PENDING
    )

    private val _tasks = MutableStateFlow<List<TaskState>>(emptyList())
    val tasks: StateFlow<List<TaskState>> = _tasks.asStateFlow()

    fun enqueue(label: String, work: suspend () -> Boolean) {
        val id = System.currentTimeMillis() + Random.nextLong(0, 1000)
        _tasks.update { it + TaskState(id = id, label = label) }
        scope.launch {
            processTask(id, label, work)
        }
    }

    private suspend fun processTask(id: Long, label: String, work: suspend () -> Boolean) {
        var attempt = 0
        while (attempt < maxRetries) {
            attempt += 1
            val status = if (attempt == 1) Status.RUNNING else Status.RETRYING
            updateState(id) { it.copy(status = status, attempts = attempt) }
            val ok = try {
                work()
            } catch (e: Exception) {
                Log.w("UploadQueue", "task $label failed on attempt $attempt: ${e.message}")
                false
            }
            if (ok) {
                updateState(id) { it.copy(status = Status.SUCCESS, attempts = attempt) }
                return
            }
            if (attempt >= maxRetries) {
                updateState(id) { it.copy(status = Status.FAILED, attempts = attempt) }
                return
            }
            delay(baseDelayMs * attempt)
        }
    }

    private fun updateState(id: Long, updater: (TaskState) -> TaskState) {
        _tasks.update { list ->
            list.map { if (it.id == id) updater(it) else it }
        }
    }
}
