function validateForm() {

    let title = document.forms["createForm"]["title"].value;
    let body = document.forms["createForm"]["body"].value;


    if (title.trim() == "") {
        alert("제목을 입력해주세요.");

        return false;
    }

    if (body.trim() == "") {
        alert("내용을 입력해주세요.");

        return false;
    }

    return true;
}

function togglePasswordField() {
                var checkBox = document.getElementById("is_secret");
                var passwordField = document.getElementById("password_field");
                if (checkBox.checked == true){
                    passwordField.style.display = "block";
                } else {
                    passwordField.style.display = "none";
                }
            }
