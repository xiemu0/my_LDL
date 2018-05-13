# LDL-SCL based on gradient descent
import scipy.io as sio
from sklearn.cluster import KMeans
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from utils.evaluation_metrics import *


# read data set .mat
def read_mat(url):
    data = sio.loadmat(url)
    return data


# cluster
def cluster_ave(labels_train, n):
    train_len = len(labels_train)
    kmeans = KMeans(n_clusters=n, random_state=0).fit(labels_train)
    predict = kmeans.predict(labels_train)
    classification = []
    for i in range(n):
        classification.append([])
    c = np.zeros([train_len, n]) + 10 ** -6
    for i in range(train_len):
        c[i][predict[i]] = 1
        classification[predict[i]].append(labels_train[i])
    p = []
    for i in range(n):
        p.append(np.average(classification[i], 0))
    p = np.array(p)
    return c, p


# x: matrix of feature, n * d
# theta: weight matrix of feature, d * l, l is the number of labels
# c: matrix of code, n * m, m is the number of clusters
# w: weight matrix of code matrix, m * l
def predict_func(x, theta, c, w):
    matrix = np.dot(x, theta) + np.dot(c, w)
    matrix1 = matrix - np.max(matrix, 1).reshape(-1, 1)
    numerator = np.exp(matrix1)
    denominator = np.sum(np.exp(matrix1), 1).reshape(-1, 1)
    return numerator / denominator


# label_real: real label of instance, n * l
# p: the average vector of cluster, number of clusters * l
def optimize_func(x, theta, c, w, label_real, p, lambda1, lambda2, lambda3, mu):
    label_predict = predict_func(x, theta, c, w) + 10 ** -6
    term1 = np.sum(label_real * np.log((label_real + 10 ** -6) / (label_predict + 10 ** -6)))
    term2 = np.sum(theta ** 2)
    term3 = np.sum(w ** 2)
    dist = []
    for i in range(len(p)):
        dist.append(np.sum((label_predict - p[i]) ** 2, 1))
    dist = np.array(dist).T
    term4 = np.sum(c * dist)
    term5 = np.sum(1. / c)
    return term1 + lambda1 * term2 + lambda2 * term3 + lambda3 * term4 + mu * term5


# m: the row of theta
# n: the column of theta
def gradient_theta(x, theta, c, w, label_real, p, m, n, lambda1, lambda2, lambda3):
    # the first term
    gradient1 = np.sum((predict_func(x, theta, c, w)[:, n] - label_real[:, n]) * x[:, m])
    # the second term
    gradient2 = 2 * lambda1 * theta[m][n]
    # the third term
    gradient3 = 0.
    for i in range(len(x)):
        for j in range(len(p)):
            denominator = np.sum(np.exp(np.dot(x[i], theta) + np.dot(c[i], w)))
            p_i_n = np.exp(np.dot(x[i], theta) + np.dot(c[i], w))[n] / denominator
            gradient3 += c[i][j] * (p_i_n-p[j][n]) * x[i][m] * (p_i_n-p_i_n**2)
    gradient3 *= 2*lambda3
    return gradient1 + gradient2 + gradient3


def gradient_w(x, theta, c, w, label_real, p, m, n, lambda1, lambda2, lambda3):
    # the first term
    gradient1 = np.sum((predict_func(x, theta, c, w)[:, n] - label_real[:, n]) * c[:, m])
    # the second term
    gradient2 = 2 * lambda2 * w[m][n]
    # the third term
    gradient3 = 0.
    for i in range(len(x)):
        for j in range(len(p)):
            denominator = np.sum(np.exp(np.dot(x[i], theta) + np.dot(c[i], w)))
            p_i_n = np.exp(np.dot(x[i], theta) + np.dot(c[i], w))[n] / denominator
            gradient3 += c[i][j] * (p_i_n-p[j][n]) * c[i][m] * (p_i_n-p_i_n**2)
    gradient3 *= 2*lambda3
    return gradient1 + gradient2 + gradient3


def gradient_c(x, theta, c, w, label_real, p, m, n, lambda1, lambda2, lambda3, mu):
    # the first term
    gradient1 = -np.sum(label_real[m] * w[n])
    # the second term
    numerator = np.sum(np.exp(np.dot(x[m], theta) + np.dot(c[m], w)) * w[n])
    denominator = np.sum(np.exp(np.dot(x[m], theta) + np.dot(c[m], w)))
    gradient2 = numerator / denominator
    # the third term
    gradient3 = 0.
    for l in range(len(label_real[0])):
        denominator = np.sum(np.exp(np.dot(x[m], theta) + np.dot(c[m], w)))
        p_i_l = np.exp(np.dot(x[m], theta) + np.dot(c[m], w))[l] / denominator
        numerator1 = np.sum(np.exp(np.dot(x[m], theta) + np.dot(c[m], w)) * w[n])
        partial_c = p_i_l * (w[n][l] - numerator1/denominator)
        gradient3 += (p_i_l - p[n][l]) * partial_c
    gradient3 *= 2 * lambda3 * c[m][n]
    # the fourth term
    denominator = np.sum(np.exp(np.dot(x[m], theta) + np.dot(c[m], w)))
    p_i = np.exp(np.dot(x[m], theta) + np.dot(c[m], w)) / denominator
    gradient4 = lambda3 * np.sum((p_i - p[n]) ** 2)
    # the fifth term
    gradient5 = -mu * c[m][n] ** (-2)
    return gradient1 + gradient2 + gradient3 + gradient4 + gradient5


if __name__ == "__main__":
    # configuration
    lambda1 = 0.001
    lambda2 = 0.001
    lambda3 = 0.001
    code_len = 5

    data1 = read_mat(r"../datasets/Yeast_cold.mat")
    features = data1["features"]
    label_real1 = data1["labels"]
    features_dim = len(features[0])
    labels_dim = len(label_real1[0])

    result1 = []
    result2 = []
    result3 = []
    result4 = []
    result5 = []
    result6 = []

    loss_arr = []
    for t in range(10):
        mu = 1
        theta1 = np.ones([features_dim, labels_dim])
        w1 = np.ones([code_len, labels_dim])

        x_train, x_test, y_train, y_test = train_test_split(features, label_real1, test_size=0.2, random_state=t)
        c1, p1 = cluster_ave(y_train, code_len)

        loss1 = optimize_func(x_train, theta1, c1, w1, y_train, p1, lambda1, lambda2, lambda3, mu)

        # train starts
        for i in range(100):
            gradient1 = []
            for m1 in range(features_dim):
                for n1 in range(labels_dim):
                    gradient1.append(gradient_theta(x_train, theta1, c1, w1, y_train, p1, m1, n1, lambda1, lambda2, lambda3))
            gradient1 = np.array(gradient1).reshape(features_dim, labels_dim)
            gradient1 = gradient1 / np.sqrt(np.sum(gradient1 ** 2))

            gradient2 = []
            for m1 in range(code_len):
                for n1 in range(labels_dim):
                    gradient2.append(gradient_w(x_train, theta1, c1, w1, y_train, p1, m1, n1, lambda1, lambda2, lambda3))
            gradient2 = np.array(gradient2).reshape(code_len, labels_dim)
            gradient2 = gradient2 / np.sqrt(np.sum(gradient2 ** 2))

            gradient3 = []
            for m1 in range(len(x_train)):
                for n1 in range(code_len):
                    gradient3.append(gradient_c(x_train, theta1, c1, w1, y_train, p1, m1, n1, lambda1, lambda2, lambda3, mu))
            gradient3 = np.array(gradient3).reshape(len(x_train), code_len)
            gradient3 = gradient3 / np.sqrt(np.sum(gradient3 ** 2))

            theta1 = theta1 - 0.05 * gradient1
            w1 = w1 - 0.05 * gradient2
            c1 = c1 - 0.05 * gradient3
            # print(predict_func(x_train, theta1, c1, w1))

            loss2 = optimize_func(x_train, theta1, c1, w1, y_train, p1, lambda1, lambda2, lambda3, mu)
            print(loss2)
            # print(kl(label_real1, predict_func(x1, theta1, c1, w1)))
            # if np.abs(loss2 - loss1) < 0.001 or loss2 > loss1 or mu*np.sum(1. / c1) < 10 ** -9:
            if np.abs(loss2 - loss1) < 0.001 or loss2 > loss1:
                break
            else:
                mu = mu * 0.1
            loss1 = loss2
            loss_arr.append(loss1)
            print("*" * 50, i)

        # print(theta1)
        # print(w1)
        # print(c1)

        # test starts
        regression = []
        for i in range(code_len):
            lr = LinearRegression()
            lr.fit(x_train, c1[:, i].reshape(-1, 1))
            regression.append(lr)
        codes = []
        for i in range(len(x_test)):
            for lr1 in regression:
                codes.append(lr1.predict(x_test[i].reshape(1, -1)))
        codes = np.array(codes).reshape(len(x_test), code_len)
        label_pre = predict_func(x_test, theta1, codes, w1)
        # print(label_pre)
        print(euclidean(y_test + 10 ** -6, label_pre + 10 ** -6))
        result1.append(euclidean(y_test + 10 ** -6, label_pre + 10 ** -6))
        print(sorensen(y_test + 10 ** -6, label_pre + 10 ** -6))
        result2.append(sorensen(y_test + 10 ** -6, label_pre + 10 ** -6))
        print(squared_chi2(y_test + 10 ** -6, label_pre + 10 ** -6))
        result3.append(squared_chi2(y_test + 10 ** -6, label_pre + 10 ** -6))
        print(kl(y_test + 10 ** -6, label_pre + 10 ** -6))
        result4.append(kl(y_test + 10 ** -6, label_pre + 10 ** -6))
        print(intersection(y_test + 10 ** -6, label_pre + 10 ** -6))
        result5.append(intersection(y_test + 10 ** -6, label_pre + 10 ** -6))
        print(fidelity(y_test + 10 ** -6, label_pre + 10 ** -6))
        result6.append(fidelity(y_test + 10 ** -6, label_pre + 10 ** -6))

    print(result1)
    print(result2)
    print(result3)
    print(result4)
    print(result5)
    print(result6)
    print("*" * 50)
    print("euclidean:", np.mean(result1))
    print("euclidean:", np.std(result1))
    print("-" * 50)
    print("sorensen:", np.mean(result2))
    print("sorensen:", np.std(result2))
    print("-" * 50)
    print("squared_chi2:", np.mean(result3))
    print("squared_chi2:", np.std(result3))
    print("-" * 50)
    print("kl:", np.mean(result4))
    print("kl:", np.std(result4))
    print("-" * 50)
    print("intersection:", np.mean(result5))
    print("intersection:", np.std(result5))
    print("-" * 50)
    print("fidelity:", np.mean(result6))
    print("fidelity:", np.std(result6))



