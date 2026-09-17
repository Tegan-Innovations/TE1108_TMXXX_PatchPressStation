// Keep these lines for a best effort IntelliSense of Visual Studio 2017 and higher.
/// <reference path="./../../../Packages/Beckhoff.TwinCAT.HMI.Framework.14.3.431/runtimes/native1.12-tchmi/TcHmi.d.ts" />
//sysManag.js



async function userManager(User, Password, Group, slctUser, Action){
    try{
        const userData = User;
        const passwordData = Password;
        const groupData = Group;
        const act = Action;
        const oldUser = slctUser;
        var   groupName = '';
        var   LogOutTime = "";  

        if(groupData == '1'){
	        groupName = 'Administrator';
            LogOutTime = "PT15M";
        }
        if(groupData == '2'){
	        groupName = 'Engineer';
            LogOutTime = "PT15M";
        }
        if(groupData == '3'){
	        groupName = 'Operator';
            LogOutTime = "P30D";
        }

        // ========================================================
        // PASSO ATUAL: VALIDAÇÃO DE DUPLICIDADE APENAS PARA ADDUSER
        // ========================================================
        if (act == 'addUser') {
            // 1. Bloqueio básico caso esqueçam de preencher os campos na tela
            if (!userData || !passwordData || !groupName) {
                alert("Validation Notice: Please fill in the Username, Password, and select a Group.");
                return; 
            }
        }

        if(act == 'addUser'){
            // 1. Lê a lista de usuários mapeada no servidor através do símbolo real 'ListUsers'
            TcHmi.Symbol.readEx2('%s%TcHmiUserManagement.ListUsers%/s%', function(data) {
                
                if (data.error === TcHmi.Errors.NONE) {
                    // O data.result trará o array de strings com os nomes dos usuários existentes (ex: ["__SystemAdministrator", "uu11"])
                    const userListArray = data.result;

                    if (Array.isArray(userListArray)) {
                        // 2. Verifica se o nome digitado (User) já está incluso na lista do servidor
                        if (userListArray.includes(User)) {
                            alert("Validation Error: The username '" + User + "' already exists in the system.");
                            return; // Aborta e impede o avanço para a criação do duplicado
                        }
                    }
                }

                // 3. Se passou pela validação (não existe), executa o addUserEx nativo do framework
                TcHmi.Server.UserManagement.addUserEx(
                    User, 
                    Password, 
                    {groups: [groupName], enabled: true, locale: 'de', autoLogout: LogOutTime },
                    {timeout: 2000},
                    function(dataAdd) {
                        if (dataAdd.error === TcHmi.Errors.NONE) {
                            alert('User created successfully.');
                        } else {
                            alert("Server Error: Failed to add the new user. Code: " + dataAdd.error);
                        }
                    }
                );
            });
            console.log(act);
        }
        if(act == 'removeUser'){
            TcHmi.Server.UserManagement.removeUserEx (
                User, 
                null,
                {timeout: 2000},
                function(data) {
                    if (data.error === TcHmi.Errors.NONE) {
                        alert.log('User removed successfully.');
                    } else {
                        alert("Server Error: Failed to remove the selected user. Code: " + data.error);
                    }
                }
            );
        }
        if(act == 'changeName'){
            TcHmi.Server.UserManagement.updateUser(
                oldUser, 
                {
                newName: User
                },
                function(data) {
                    if (delData.error === TcHmi.Errors.NONE) {
                        alert.log('User renamed successfully.');
                    } else {
                        lert("Server Critical Error: New identity established, but the legacy account couldn't be purged. Code: " + delData.error);
                    }
                }
            );
        }
        if(act == 'addGroup'){
            TcHmi.Server.UserManagement.updateUser(
                oldUser, 
                {
                addGroups: [groupName]
                },
                function(data) {
                    if (data.error === TcHmi.Errors.NONE) {
                        alert.log('Group association added.'); 
                    } else {
                        alert("Server Error: Failed to attach group to user profile. Code: " + data.error);
                    }
                }
            );
        }
        if(act == 'removeGroup'){
            TcHmi.Server.UserManagement.updateUser(
                oldUser, 
                {
                removeGroups: [groupName]
                },
                function(data) {
                    if (data.error === TcHmi.Errors.NONE) {
                        alert.log('Group association removed.'); 
                    } else {
                        alert("Server Error: Failed to detach group from user profile. Code: " + data.error);
                    }
                }
            );
        }
        if(act == 'changePassword'){
            TcHmi.Server.UserManagement.updateUser(
                oldUser, 
                {
                password: passwordData
                },
                function(data) {
                    if (data.error === TcHmi.Errors.NONE) {
                        alert.log('Credentials updated.'); 
                    } else {
                        alert("Server Error: Password update rejected by server. Code: " + data.error);
                    }
                }
            );
        }

        console.log(userData);
        console.log(passwordData);
        console.log(groupData);

    } catch (erro){
        alert("Fatal Application Exception: " + erro.message);
    }
};
