// Mail Agent JavaScript functionality - Bootstrap 5 compatible
let currentInstructionId = null;

function openNewInstructionModal() {
    const modal = new bootstrap.Modal(document.getElementById('newInstructionModal'));
    modal.show();
    toggleNameField('new');
}

function closeNewInstructionModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('newInstructionModal'));
    if (modal) {
        modal.hide();
    }
    document.getElementById('newInstructionForm').reset();
}

function openEditModal(instructionId) {
    currentInstructionId = instructionId;
    
    // Fetch instruction data
    fetch(`/instructions/get/${instructionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            
            // Populate form
            document.getElementById('editInstructionType').value = data.instruction_type;
            document.getElementById('editInstructionName').value = data.name;
            document.getElementById('editInstructionContent').value = data.content;
            
            // Set form action
            document.getElementById('editInstructionForm').action = `/instructions/update/${instructionId}`;
            
            // Toggle name field visibility
            toggleNameField('edit');
            
            // Show modal using Bootstrap
            const modal = new bootstrap.Modal(document.getElementById('editInstructionModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Failed to load instruction data');
        });
}

function closeEditModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('editInstructionModal'));
    if (modal) {
        modal.hide();
    }
    currentInstructionId = null;
}

function deleteInstruction() {
    if (currentInstructionId && confirm('Are you sure you want to delete this instruction?')) {
        window.location.href = `/instructions/delete/${currentInstructionId}`;
    }
}

function toggleNameField(formType) {
    const typeSelect = document.getElementById(formType + 'InstructionType');
    const nameGroup = document.getElementById(formType + 'NameGroup');
    
    if (typeSelect.value === 'system') {
        nameGroup.style.display = 'none';
    } else {
        nameGroup.style.display = 'block';
    }
}

// Remove the old window.onclick handler since Bootstrap handles backdrop clicks
// Initialize name field visibility
document.addEventListener('DOMContentLoaded', function() {
    toggleNameField('new');
});
