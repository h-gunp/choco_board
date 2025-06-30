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
